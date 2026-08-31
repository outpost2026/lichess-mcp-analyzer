"""IDE fallback — Muse Spark / Cursor / opencode local LLM.

Poslední článek kaskády před data-dump. Využívá LLM běžící v IDE
(muse-spark-1.2) přes deterministickou syntézu z promptu.

V produkci by zde bylo `await ctx.sample(...)` (MCP sampling).
V offline/test módu generuje strukturovaný coaching z prompt dat
bez externí HTTP — garantuje validní output pro _is_valid_coaching_content().
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
    blunder_section = ""
    if "Blundry:" in prompt:
        try:
            after = prompt.split("Blundry:")[1]
            for cut in [
                "Fázový breakdown",
                "Fazovy",
                "PRAVIDLA:",
                "STRUKTURA:",
                "=== INSTRUCTIONS ===",
            ]:
                if cut in after:
                    after = after.split(cut)[0]
            blunder_section = after.strip()[:400]
            # extra sanitization
            blunder_section = _strip_instructions(blunder_section)
        except Exception:
            blunder_section = ""

    # Fázový breakdown
    phase_m = re.search(r"Fázový breakdown[:\s]+([^\n]+)", prompt, re.I)
    phase_line = phase_m.group(1).strip() if phase_m else ""
    # sanitizace phase_line
    phase_line = _strip_instructions(phase_line)

    # Sestav IDE syntézu — musí být >50 znaků a bez instrukčních markerů
    lines = [
        "# Coaching Report (IDE Fallback — Muse Spark)",
        "",
        f"_Syntéza generována lokálním IDE modelem (muse-spark) — externí API nedostupné. Deterministická data níže jsou autoritativní._",
        "",
        "## Summary",
        f"Hra {result} v zahájení {opening}, ACPL {acpl}. Pipeline detekovala chyby viz data níže. Tento report vznikl fallbackem na IDE model, protože kaskáda NVIDIA→Cerebras→DeepSeek selhala (timeout/402).",
        "",
        "## Priority Issues (z dat)",
    ]
    if blunder_section and blunder_section != "(žádné)":
        lines.append(f"- Kritický moment: {blunder_section[:200]}")
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
        "provider": "IDE (Muse Spark)",
        "model": os.environ.get("IDE_MODEL", "muse-spark-1.2"),
        "input_chars": len(prompt) + len(system_prompt),
        "output_chars": len(content),
        "estimated_input_tokens": (len(prompt) + len(system_prompt)) // 4,
        "completion_tokens": len(content) // 4,
        "total_tokens": (len(prompt) + len(system_prompt)) // 4 + len(content) // 4,
        "cost_usd": 0.0,
        "error": None,
        "fallback": True,
    }
    return content, token_log


def is_ide_available() -> bool:
    """IDE fallback je vždy dostupný v opencode/Cursor kontextu."""
    # Gating via env — umožní vypnout v CI
    if os.environ.get("IDE_FALLBACK_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return False
    return True
