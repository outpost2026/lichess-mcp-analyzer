"""On-demand persistence of coaching outputs via the automatic LLM cascade.

Wraps the existing coaching MCP tools (single_game, cross_game, opponent_pool,
training_plan, opening_report) and the CLI diagnosis flow. Re-runs the same
pipeline (cache-first Stockfish data -> prompt -> LLM provider cascade) and
persists the result:

  - data/reports/{kind}_{ref}_{ts}.json                 (structured artifact)
  - docs/coaching_report_{kind}_{ref}_{ts}.md           (human-readable)
  - B2B-Knowledge-Base (02_ANALYZY/02_chess, 04_KNOWLEDGE_BASE/02_chess)
    when target="kb" and kind is diagnosis/cross_game

Every write is verified read-after-write (AGENTS.md 2.5): missing file or
empty size => error, never silent success.
"""

import json
import os
from datetime import UTC, datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
REPORTS_DIR = os.path.join(REPO_ROOT, "data", "reports")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")

KINDS = {
    "single_game",
    "cross_game",
    "opponent_pool",
    "training_plan",
    "opening_report",
    "diagnosis",
}
FORMATS = {"json", "md", "both"}
TARGETS = {"docs", "kb"}


def _ts() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def _ref_for(kind: str, params: dict) -> str:
    if params.get("game_id"):
        return params["game_id"]
    if params.get("username"):
        return params["username"]
    if params.get("game_ids"):
        return f"pool_{len(params['game_ids'])}"
    return "anon"


def _write_verified(path: str, content: str) -> dict:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise OSError(f"read-after-write verification failed: {path}")
    return {"path": path, "size_bytes": os.path.getsize(path)}


def _provider_label(cascade_log: list[dict]) -> str:
    if not cascade_log:
        return "n/a"
    for entry in reversed(cascade_log):
        if entry.get("provider") and not entry.get("error"):
            return entry["provider"]
    return "fallback (data dump)"


def _build_md(kind: str, ref: str, result: dict) -> str:
    lines = [
        f"# Coaching Report — {kind} ({ref})",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "**Pipeline:** deterministic (Stockfish) + LLM cascade",
        f"**LLM provider:** {_provider_label(result.get('cascade_log', []))}",
    ]
    if result.get("games_analyzed") is not None:
        lines.append(f"**Games analyzed:** {result['games_analyzed']}")
    if result.get("opening_stats"):
        lines.append(
            f"**Opening stats:** {json.dumps(result['opening_stats'], ensure_ascii=False)}"
        )
    lines += ["", "---", ""]

    patterns = result.get("patterns") or []
    if patterns:
        lines.append(f"## Patterns ({len(patterns)})")
        lines.append("")
        lines.append("| Pattern | Name | Confidence | Frequency | Severity |")
        lines.append("|---------|------|------------|-----------|----------|")
        for p in patterns:
            lines.append(
                f"| {p.get('pattern_id', '?')} | {p.get('pattern_name', '?')} | "
                f"{p.get('confidence', '?')}% | {p.get('frequency', '?')} | "
                f"{p.get('severity', '?').upper()} |"
            )
        lines.append("")
    else:
        lines.append("*No patterns detected.*")
        lines.append("")

    weakness = result.get("weakness")
    if weakness:
        lines.append("## Weakness Report")
        lines.append("")
        lines.append(f"- Total ACPL: {weakness.get('total_acpl', '?')}")
        lines.append(f"- Blunders: {weakness.get('blunder_count', '?')}")
        lines.append(f"- Mistakes: {weakness.get('mistake_count', '?')}")
        lines.append(f"- Inaccuracies: {weakness.get('inaccuracy_count', '?')}")
        lines.append("")

    lines += ["---", "", "## LLM Report", ""]
    lines.append(result.get("report", "_empty report_"))

    cascade_log = result.get("cascade_log") or []
    if cascade_log:
        lines += ["", "---", "", "## Provider Cascade", ""]
        lines.append("| # | Provider | Status | Tokens | Cost (USD) |")
        lines.append("|---|----------|--------|--------|-----------|")
        for i, entry in enumerate(cascade_log):
            prov = entry.get("provider", "?")
            if entry.get("error"):
                lines.append(f"| {i + 1} | {prov} | ERROR: {entry['error'][:60]} | - | - |")
            else:
                tokens = entry.get("total_tokens", entry.get("estimated_input_tokens", "?"))
                cost = entry.get("cost_usd", 0)
                lines.append(f"| {i + 1} | {prov} | OK | {tokens} | {cost} |")
    return "\n".join(lines)


def _kb_pattern_slim(patterns: list[dict]) -> list[dict]:
    return [
        {
            "pattern_id": p.get("pattern_id"),
            "pattern_name": p.get("pattern_name"),
            "confidence": round(p.get("confidence", 0) / 100, 2),
            "severity": p.get("severity"),
        }
        for p in patterns
    ]


def _write_kb(kind: str, ref: str, result: dict) -> list[dict]:
    from lichess_analyzer_mcp.kb.writer import (
        write_analysis_report,
        write_pattern_report,
    )

    artifacts = []
    patterns = result.get("patterns") or []
    if patterns:
        path = write_pattern_report(ref, _kb_pattern_slim(patterns))
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise OSError(f"read-after-write verification failed: {path}")
        artifacts.append({"path": path, "size_bytes": os.path.getsize(path)})

    weakness = result.get("weakness")
    if weakness and kind in ("diagnosis", "cross_game"):
        report = {
            "games_analyzed": result.get("games_analyzed", 0),
            "total_acpl": weakness.get("total_acpl", 0),
            "blunders": weakness.get("blunder_count", 0),
            "mistakes": weakness.get("mistake_count", 0),
            "inaccuracies": weakness.get("inaccuracy_count", 0),
            "phase_weaknesses": weakness.get("phase_weaknesses", {}),
            "leaky_openings": weakness.get("leaky_openings", []),
            "top_weaknesses": weakness.get("top_weaknesses", []),
        }
        path = write_analysis_report(ref, report)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise OSError(f"read-after-write verification failed: {path}")
        artifacts.append({"path": path, "size_bytes": os.path.getsize(path)})
    return artifacts


async def _run_tool(kind: str, params: dict) -> dict:
    if kind == "single_game":
        from lichess_analyzer_mcp.tools.coaching_single_game import lichess_coaching_single_game

        return await lichess_coaching_single_game(
            params.get("game_id", ""),
            params.get("color", "white"),
            params.get("depth", 0),
        )
    if kind == "cross_game":
        from lichess_analyzer_mcp.tools.coaching_cross_game import lichess_coaching_cross_game

        return await lichess_coaching_cross_game(
            params.get("username", ""),
            params.get("max_games", 20),
            params.get("depth", 0),
            params.get("result", "all"),
        )
    if kind == "opponent_pool":
        from lichess_analyzer_mcp.tools.coaching_opponent_pool import lichess_coaching_opponent_pool

        return await lichess_coaching_opponent_pool(
            ",".join(params.get("game_ids", [])),
            params.get("depth", 0),
        )
    if kind == "training_plan":
        from lichess_analyzer_mcp.tools.coaching_training_plan import lichess_coaching_training_plan

        return await lichess_coaching_training_plan(
            params.get("username", ""),
            params.get("max_games", 20),
            params.get("hours_per_week", 5),
            params.get("rating", 0),
            params.get("depth", 0),
            params.get("result", "all"),
        )
    if kind == "opening_report":
        from lichess_analyzer_mcp.tools.coaching_opening_report import (
            lichess_coaching_opening_report,
        )

        return await lichess_coaching_opening_report(
            params.get("username", ""),
            params.get("max_games", 20),
            params.get("depth", 0),
            params.get("result", "all"),
        )
    raise ValueError(f"unsupported kind: {kind}")


async def _run_diagnosis(params: dict) -> dict:
    from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
    from lichess_analyzer_mcp.services.coaching_base import (
        collect_patterns_for_games,
        collect_weakness_report,
    )
    from lichess_analyzer_mcp.services.game_analyzer import _load_cached_analysis, analyze_pgn
    from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn, fetch_user_games
    from lichess_analyzer_mcp.services.llm_client import generate_coaching_report_with_logs
    from lichess_analyzer_mcp.services.logger import get_logger

    log = get_logger("report_persister")
    username = params.get("username", "")
    max_games = max(5, min(50, params.get("max_games", 20)))
    depth = params.get("depth", 0) or DEPTH_DEFAULTS["batch"]["diagnose"]
    depth = max(DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_batch"], depth))

    if not username:
        return {"error": "Provide username for kind=diagnosis"}

    games_data = fetch_user_games(username, max_games=max_games, result=params.get("result", "all"))
    analyses = []
    for g in games_data[:max_games]:
        game_id = g.get("id", "")
        try:
            color = "white"
            if (
                g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
                == username.lower()
            ):
                color = "black"
            cached = _load_cached_analysis(game_id, depth, color)
            if cached is not None:
                analyses.append(cached)
                continue
            pgn = fetch_game_pgn(game_id)
            a = analyze_pgn(pgn, player_color=color, depth=depth, game_id=game_id)
            if a:
                analyses.append(a)
        except Exception as e:
            log.warning("skip %s: %s", game_id, e)

    if not analyses:
        return {"error": "No games could be analyzed"}

    patterns = collect_patterns_for_games(analyses, username)
    weakness = collect_weakness_report(analyses, username)
    report, cascade_log = generate_coaching_report_with_logs(
        username=username,
        games_analyzed=len(analyses),
        patterns=patterns,
        weakness_report=weakness,
    )
    return {
        "username": username,
        "games_analyzed": len(analyses),
        "report": report,
        "patterns": patterns,
        "weakness": weakness,
        "cascade_log": cascade_log,
    }


async def persist_report(kind: str, params: dict, fmt: str = "both", target: str = "docs") -> dict:
    """Generate (via LLM cascade) and persist coaching output.

    Returns artifact metadata; raises on write verification failure.
    """
    if kind not in KINDS:
        return {"error": f"kind must be one of: {sorted(KINDS)}"}
    if fmt not in FORMATS:
        return {"error": f"format must be one of: {sorted(FORMATS)}"}
    if target not in TARGETS:
        return {"error": f"target must be one of: {sorted(TARGETS)}"}

    if kind == "diagnosis":
        result = await _run_diagnosis(params)
    else:
        result = await _run_tool(kind, params)
    if not isinstance(result, dict) or "error" in result:
        return result if isinstance(result, dict) else {"error": str(result)}

    ref = _ref_for(kind, params)
    ts = _ts()
    artifacts = []

    if fmt in ("json", "both"):
        payload = json.dumps(result, ensure_ascii=False, indent=2)
        artifacts.append(
            _write_verified(os.path.join(REPORTS_DIR, f"{kind}_{ref}_{ts}.json"), payload)
        )
    if fmt in ("md", "both"):
        md = _build_md(kind, ref, result)
        artifacts.append(
            _write_verified(os.path.join(DOCS_DIR, f"coaching_report_{kind}_{ref}_{ts}.md"), md)
        )
    if target == "kb":
        artifacts.extend(_write_kb(kind, ref, result))

    return {
        "kind": kind,
        "ref": ref,
        "timestamp": ts,
        "artifacts": artifacts,
        "cascade_log": result.get("cascade_log", []),
    }
