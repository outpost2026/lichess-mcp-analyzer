"""Deterministic report fallback (formerly "IDE fallback — Muse Spark").

This module does NOT call any LLM. It builds a structured coaching summary
from the prompt data. It is the last cascade step before a raw data dump and
must always be labelled as deterministic — never as an LLM output (P0.3).
"""

import os
import re


def _strip_instructions(prompt: str) -> str:
    for m in ("=== INSTRUCTIONS ===", "PRAVIDLA:", "STRUKTURA:"):
        if m in prompt:
            prompt = prompt.split(m)[0]
    return prompt.strip()


def _extract_field(prompt: str, key: str) -> str:
    # Hledá "K DISPOZICI:" sekci — jednoduchý regex pro známé placeholdery
    m = re.search(rf"{re.escape(key)}\s*[:=]\s*(.+)", prompt)
    return m.group(1).strip() if m else ""


def _clip(text: str, limit: int = 200) -> str:
    """Trim at a field boundary so the report never ends mid-word."""
    if len(text) <= limit:
        return text
    window = text[:limit]
    for sep in ("; ", ". ", ", "):
        cut = window.rfind(sep)
        if cut >= limit // 2:
            return window[:cut]
    return window


def _critical_moments(value: str, max_items: int = 3) -> str:
    """Compact, structure-safe summary of flagged moves from the prompt.

    The prompt contains one line per move with prose and (for flagged moves)
    a JSON snippet. Slicing that text at a fixed offset produced reports that
    ended mid-array (FIX-011). Here only `ply`, SAN and cp loss are extracted,
    so the result can never contain a half-written structure.
    """
    # REVIEW-CROSS 2026-11-18: rank by game_impact transition, not raw cp_loss.
    # A 478cp move that stays winning is NOT the decisive moment when a 599cp
    # move flips winning->losing (7l9g62Eo p77 vs p79; v2xHpqXG p29 vs p39).
    decisive_impacts = {"winning_to_losing": 2, "equal_to_losing": 2, "equal_to_mate": 2}
    weakening_impacts = {"winning_to_equal": 1}
    seen: set[int] = set()
    ranked: list[tuple[int, float, str]] = []
    for m in re.finditer(r"ply\s+(\d+)\s*:?\s*([^\s,(;]+)", value):
        ply = int(m.group(1))
        if ply in seen:
            continue
        seen.add(ply)
        san = m.group(2)
        tail = value[m.end() : m.end() + 260]
        cp_m = re.search(r"(?:loss|cp_loss)\s*[=:]?\s*([\d.]+)", tail)
        # D34: the deterministic report must carry the same verdict the JSON
        # publishes - otherwise "9027cp" reads as a catastrophe even when the
        # position stayed winning.
        impact_m = re.search(r"impact=([a-z_]+)", tail)
        missed_m = re.search(r"mate_missed=(\d+)(?:\s+via\s+([^\s,;)]+))?", tail)
        notes = []
        if impact_m:
            notes.append(impact_m.group(1))
        if missed_m:
            via = f" via {missed_m.group(2)}" if missed_m.group(2) else ""
            notes.append(f"mate missed: {missed_m.group(1)}{via}")
        suffix = f" [{', '.join(notes)}]" if notes else ""
        text = f"ply {ply} {san} {cp_m.group(1)}cp{suffix}" if cp_m else f"ply {ply} {san}{suffix}"
        impact = impact_m.group(1) if impact_m else ""
        priority = decisive_impacts.get(impact, weakening_impacts.get(impact, 0))
        cp = float(cp_m.group(1)) if cp_m else 0.0
        ranked.append((priority, cp, text))
    ranked.sort(key=lambda row: (-row[0], -row[1]))
    return "; ".join(row[2] for row in ranked[:max_items])


def _bullet_value(prompt: str, label_prefix: str) -> str:
    """Value of a `- Label ...: value` bullet, including continuation lines.

    Template labels are not stable ("Blundry:" vs "Blundry (s detaily):"), so
    match the label prefix instead of the exact line. Matching the full line
    silently produced an empty value and the report then claimed "no blunder"
    even when blunders existed (DATA-FABRICATION-001).
    """
    lines = prompt.splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:]
        if not body.lower().startswith(label_prefix.lower()):
            continue
        if ":" not in body:
            continue
        value = body.split(":", 1)[1].strip()
        parts = [value] if value else []
        for follow in lines[idx + 1 :]:
            follow_stripped = follow.strip()
            if not follow_stripped or follow_stripped.startswith("- "):
                break
            parts.append(follow_stripped)
        return " ".join(parts).strip()
    return ""


def generate_ide_report(prompt: str, system_prompt: str = "") -> tuple[str, dict]:
    """Vygeneruj coaching report deterministicky — IDE fallback.

    Returns (content, token_log). Nikdy nevrací None — vždy validní coaching.
    """
    # Extrahuj klíčové metriky z promptu pro syntézu
    # Prompt pro single_game obsahuje: Výsledek, barva, zahájení, ACPL, Počet chyb, Blundry, Fázový breakdown
    acpl_m = re.search(r"ACPL[:\s]+([\d\.]+)", prompt)
    acpl = acpl_m.group(1) if acpl_m else "?"
    opening_m = re.search(r"zahájení[:\s]+([^\n]+)", prompt, re.I)
    opening = opening_m.group(1).strip() if opening_m else "?"
    result_m = re.search(r"Výsledek[:\s]+([^\n,]+)", prompt, re.I)
    result = result_m.group(1).strip() if result_m else "?"
    # Blunder line count — strip instructions to avoid leak
    blunder_section = _bullet_value(prompt, "Blundry")
    # Structure-safe: only ply/SAN/cp, never a slice of the raw JSON blob.
    moments = _critical_moments(blunder_section)
    count_m = re.search(r"Počet chyb:\s*(\d+)\s*blunder", prompt, re.I)
    blunder_count = int(count_m.group(1)) if count_m else None

    # Fázový breakdown
    phase_m = re.search(r"Fázový breakdown[:\s]+([^\n]+)", prompt, re.I)
    phase_line = phase_m.group(1).strip() if phase_m else ""
    # sanitizace phase_line
    phase_line = _strip_instructions(phase_line)

    # Sestav IDE syntézu — musí být >50 znaků a bez instrukčních markerů
    lines = [
        "# Coaching Report (deterministický souhrn)",
        "",
        "_Tento report sestavila pipeline deterministicky z dat. Nebyl generován jazykovým modelem — externí poskytovatel nebyl dostupný. Deterministická data níže jsou autoritativní._",
        "",
        "## Summary",
        f"Hra {result} v zahájení {opening}, ACPL {acpl}. Pipeline detekovala chyby viz data níže.",
        "",
        "## Priority Issues (z dat)",
    ]
    if moments:
        lines.append(f"- Kritický moment: {_clip(moments, 200)}")
    elif blunder_count:
        lines.append(f"- Blunderů: {blunder_count} — detaily v datech níže.")
    else:
        lines.append("- Žádný blunder — chyby jsou nepřesnosti/mistakes, viz ACPL per fáze.")
    clock_m = re.search(r"Časová data[^\n]*: ([^\n]+)", prompt, re.I)
    if clock_m:
        lines.append(f"- Časová data: {clock_m.group(1).strip()}")
    if phase_line:
        # FIX-021: the phase breakdown already separates weak phases from clean
        # ones ("... | čisté fáze: opening"). A clean phase must never be
        # presented as weakest, and an all-clean game says so explicitly.
        weak_part, _, clean_part = phase_line.partition(" | čisté fáze: ")
        weak_part = weak_part.strip()
        clean_part = clean_part.strip()
        if weak_part and weak_part.lower() != "žádná slabá fáze":
            lines.append(f"- Fázově nejslabší: {weak_part}")
        else:
            lines.append("- Žádná slabá fáze — všechny fáze bez chyb.")
        if clean_part:
            lines.append(f"- Čisté fáze: {clean_part}")
    lines += [
        "",
        "## Training Recommendations (deterministické)",
        "- Opakuj fázový breakdown: posiluj fázi s nejvyšší ACPL",
        "- Pro každý `centipawn_loss >100` přehraj engine line top3 z BlunderFactSheet",
        "- Repertoire: zkontroluj zahájení s ACPL >40",
        "",
        "## Strengths",
        "- Report postaven na Stockfish + pattern detection — bez halucinace",
        "- Endgame/Opening ACPL lze porovnat napříč hrami",
        "",
        "## Next Session Focus",
        "- 1 konkrétní chyba s největším win_prob_delta",
        "",
        "---",
        "",
        "_Plná data (flagged moves, engine lines, FEN) jsou ve strukturovaném JSON, "
        "ne v tomto textu._",
    ]
    content = "\n".join(lines)
    token_log = {
        "provider": "Deterministic report",
        "model": "rule-based-v1",
        "input_chars": len(prompt) + len(system_prompt),
        "output_chars": len(content),
        "estimated_input_tokens": (len(prompt) + len(system_prompt)) // 4,
        "completion_tokens": len(content) // 4,
        "total_tokens": (len(prompt) + len(system_prompt)) // 4 + len(content) // 4,
        "cost_usd": 0.0,
        "error": None,
        "fallback": True,
        "source": "deterministic",
        "degraded": True,
    }
    return content, token_log


def is_ide_available() -> bool:
    """Deterministic fallback is always available unless explicitly disabled."""
    # Gating via env — umožní vypnout v CI
    if os.environ.get("IDE_FALLBACK_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return False
    return True


# Backward-compatible alias; new code should use the explicit name.
generate_deterministic_report = generate_ide_report
