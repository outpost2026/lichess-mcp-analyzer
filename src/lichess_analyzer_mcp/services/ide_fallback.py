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
    data_part = _strip_instructions(prompt)

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
    blunder_section = _strip_instructions(blunder_section)[:400]
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
    if blunder_section and blunder_section.strip() not in ("(žádné)", "žádné", "-"):
        lines.append(f"- Kritický moment: {blunder_section[:200]}")
    elif blunder_count:
        lines.append(f"- Blunderů: {blunder_count} — detaily v datech níže.")
    else:
        lines.append("- Žádný blunder — chyby jsou nepřesnosti/mistakes, viz ACPL per fáze.")
    if phase_line:
        lines.append(f"- Fázově nejslabší: {phase_line}")
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
        "## Deterministic Data (Stockfish + Pattern Detection)",
        "",
        data_part,
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
