"""Per-game LLM analysis cache — Level 2 cache.

Each game gets a deep LLM analysis (blunders, phase, opening, critical moments).
These per-game analyses are cached and reused in aggregate coaching reports.
New games trigger per-game LLM only for themselves, not the entire dataset.
"""

import os, json, hashlib
from typing import Optional
from datetime import datetime, timezone

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "game_cache")

PER_GAME_SYSTEM_PROMPT = """You are a chess coach analyzing a single game.
You are given deterministic Stockfish data for ONE game.
Produce a structured game analysis in Czech.

RULES:
1. Only use data present in the input — no invented patterns or stats
2. Identify critical moments (swings >50cp)
3. Note phase-specific tendencies
4. Be specific about opening choices
5. Keep it concise (max 300 words)
6. Output as JSON with these keys: summary, phase_notes, critical_moments, opening_note, coaching_note
"""


def _game_cache_path(game_id: str, color: str, depth: int = 12) -> str:
    return os.path.join(CACHE_DIR, f"{game_id}_{color}_d{depth}.json")


def _llm_cache_path(game_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{game_id}_llm.json")


def _load_stockfish_cache(game_id: str, color: str) -> Optional[dict]:
    path = _game_cache_path(game_id, color)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_llm_cache(game_id: str) -> Optional[dict]:
    path = _llm_cache_path(game_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_llm_cache(game_id: str, data: dict) -> None:
    path = _llm_cache_path(game_id)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def _build_game_prompt(game_data: dict) -> str:
    g = game_data.get("game", {})
    moves = game_data.get("moves", [])
    blunders = game_data.get("blunders", [])
    mistakes = game_data.get("mistakes", [])
    inaccuracies = game_data.get("inaccuracies", [])
    phase_stats = game_data.get("phase_stats", {})

    lines = [
        f"Game: {g.get('id', '?')}",
        f"Color: {g.get('color', '?')}",
        f"Result: {g.get('result', '*')}",
        f"Opening: {g.get('opening', '?')}",
        f"Opponent: {g.get('opponent_name', '?')} ({g.get('opponent_rating', '?')})",
        f"Total ACPL: {game_data.get('total_acpl', 0):.1f}",
        f"Accuracy: {game_data.get('accuracy', 0):.1f}%",
        f"Moves: {len(moves)}",
        "",
    ]

    if phase_stats:
        lines.append("Phase breakdown:")
        for phase, stats in sorted(phase_stats.items()):
            lines.append(
                f"  {phase}: ACPL {stats.get('acpl', '?')}, accuracy {stats.get('accuracy', '?')}%"
            )
        lines.append("")

    errors = []
    for b in blunders:
        errors.append(
            f"BLUNDER: move {b.get('ply', '?')} {b.get('move_san', '?')} — loss {b.get('centipawn_loss', '?')}cp — {b.get('phase', '?')}"
        )
    for m in mistakes:
        errors.append(
            f"MISTAKE: move {m.get('ply', '?')} {m.get('move_san', '?')} — loss {m.get('centipawn_loss', '?')}cp — {m.get('phase', '?')}"
        )
    for i in inaccuracies:
        errors.append(
            f"INACC: move {i.get('ply', '?')} {i.get('move_san', '?')} — loss {i.get('centipawn_loss', '?')}cp — {i.get('phase', '?')}"
        )

    if errors:
        lines.append("Error moves:")
        lines.extend(errors)

    return "\n".join(lines)


def analyze_game_llm(
    game_id: str,
    color: str,
    force: bool = False,
) -> Optional[dict]:
    """Run (or load cached) per-game LLM analysis."""
    if not force:
        cached = _load_llm_cache(game_id)
        if cached:
            return cached

    game_data = _load_stockfish_cache(game_id, color)
    if not game_data:
        return None

    # Import here to avoid circular imports
    from src.services.llm_client import PROVIDERS, COACHING_SYSTEM_PROMPT, _call_llm

    system = PER_GAME_SYSTEM_PROMPT
    user = _build_game_prompt(game_data)

    # Try providers in cascade
    from src.services.llm_client import list_available_providers

    tag = _compute_content_tag(game_data)
    for prov_cfg in PROVIDERS:
        key = os.environ.get(prov_cfg["api_key_var"], "")
        if not key:
            continue
        content, log = _call_llm(system, user, prov_cfg)
        if content:
            parsed = _validate_json_output(content)
            if parsed is None:
                continue  # malformed JSON, try next provider
            result = {
                "game_id": game_id,
                "color": color,
                "model": prov_cfg["name"],
                "generated": datetime.now(timezone.utc).isoformat(),
                "llm_output": content,
                "llm_parsed": parsed,
                "token_log": log,
                "content_tag": tag,
            }
            _save_llm_cache(game_id, result)
            return result

    return None


def _validate_json_output(content: str) -> Optional[dict]:
    """Validate LLM output is parseable JSON. Extracts from ```json blocks if needed."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    # Try to extract JSON from markdown code block — outermost ```json ... ```
    start = content.find("```json")
    if start == -1:
        start = content.find("```")
    if start != -1:
        end = content.find("```", start + 3)
        if end != -1:
            block = content[start + 3 : end].strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                pass
    return None


def _compute_content_tag(game_data: dict) -> str:
    """Hash of game data to detect changes."""
    raw = json.dumps(game_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_game_summary(game_id: str) -> Optional[str]:
    """Get cached per-game LLM summary for aggregate prompt."""
    cached = _load_llm_cache(game_id)
    if not cached:
        return None
    return cached.get("llm_output", "")


def get_all_game_summaries(game_ids: list[str]) -> list[dict]:
    """Get per-game summaries for multiple games.
    Returns list of {game_id, color, acpl, blunders, llm_summary}."""
    results = []
    for gid in game_ids:
        cached = _load_llm_cache(gid)
        stockfish = None
        try:
            for fname in os.listdir(CACHE_DIR):
                if fname.startswith(gid) and fname.endswith(".json") and "_llm" not in fname:
                    try:
                        with open(os.path.join(CACHE_DIR, fname), "r", encoding="utf-8") as f:
                            stockfish = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        pass
                    break
        except FileNotFoundError:
            pass
        if stockfish:
            g = stockfish.get("game", {})
            results.append(
                {
                    "game_id": gid,
                    "color": g.get("color", "?"),
                    "acpl": stockfish.get("total_acpl", 0),
                    "blunders": len(stockfish.get("blunders", [])),
                    "llm_summary": cached.get("llm_output", "")[:300] if cached else "",
                }
            )
        elif cached:
            results.append(
                {
                    "game_id": gid,
                    "llm_summary": cached.get("llm_output", "")[:300],
                }
            )
    return results
