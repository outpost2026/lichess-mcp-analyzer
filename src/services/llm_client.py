"""LLM reasoning layer for coaching report generation.

Transforms deterministic pipeline output (PatternMatch[], WeaknessReport)
into human-readable coaching analysis. Never invents evidence — only
interprets existing data. Falls back to raw data dump when LLM unavailable.
"""

import os
from typing import Optional

LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))

COACHING_SYSTEM_PROMPT = """You are a chess coach analyzing a player's game data.
You are given DETERMINISTIC data from Stockfish analysis + pattern detection.
Your task is to produce a human-readable coaching report.

RULES (strict — never violate these):
1. DO NOT invent any evidence, patterns, or statistics not present in the data
2. DO NOT claim findings not supported by the data — use hedging language
3. You MAY group related patterns, prioritize by severity, and suggest training focus
4. Always structure output as: summary -> prioritized findings -> actionable recommendations
5. If data is ambiguous or insufficient, say so explicitly
6. Use plain language suitable for a club-level chess player (1200-1800 Elo)
7. NEVER say "you always" or "you never" — patterns are tendencies, not absolutes

Write in Czech."""


def _call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Call an OpenAI-compatible chat completion API."""
    if not LLM_API_KEY:
        return None
    import httpx

    try:
        resp = httpx.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": LLM_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLM error: {e}]"


def _build_coaching_prompt(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
) -> str:
    lines = [
        f"Player: {username}",
        f"Games analyzed: {games_analyzed}",
        "",
        "=== Pattern Detection Results ===",
    ]
    if patterns:
        for p in patterns:
            severity = p.get("severity", "?").upper()
            pid = p.get("pattern_id", "?")
            name = p.get("pattern_name", "?")
            conf = p.get("confidence", "?")
            freq = p.get("frequency", "?")
            lines.append(f"- [{severity}] {pid}: {name} (confidence: {conf}%, frequency: {freq})")
            hypothesis = p.get("hypothesis")
            if hypothesis:
                lines.append(f"  Hypothesis: {hypothesis}")
            mitigation = p.get("mitigation")
            if mitigation:
                lines.append(f"  Mitigation: {mitigation}")
            lines.append("")
    else:
        lines.append("(no patterns detected)")
        lines.append("")

    if weakness_report:
        lines.append("=== Weakness Report ===")
        wr = weakness_report
        lines.append(f"Total ACPL: {wr.get('total_acpl', '?')}")
        lines.append(f"Blunders: {wr.get('blunder_count', '?')}")
        lines.append(f"Mistakes: {wr.get('mistake_count', '?')}")
        lines.append(f"Inaccuracies: {wr.get('inaccuracy_count', '?')}")
        phase_w = wr.get("phase_weaknesses")
        if phase_w:
            lines.append("Phase breakdown:")
            for phase, stats in phase_w.items():
                lines.append(
                    f"  {phase}: ACPL {stats.get('acpl', '?')}, "
                    f"blunders {stats.get('blunders', '?')}"
                )
        leaky = wr.get("leaky_openings")
        if leaky:
            lines.append("Leaky openings:")
            for o in leaky:
                lines.append(
                    f"  {o.get('name', '?')}: {o.get('games', '?')} games, "
                    f"{o.get('blunders', '?')} blunders"
                )
        top_w = wr.get("top_weaknesses")
        if top_w:
            lines.append("Top weaknesses:")
            for w in top_w:
                lines.append(f"  - {w}")

    lines.append("")
    lines.append("=== INSTRUCTIONS ===")
    lines.append("Produce a coaching report with these sections:")
    lines.append(
        "1. **Summary** (2-3 sentences — overall player profile "
        "based strictly on detected patterns)"
    )
    lines.append(
        "2. **Priority Issues** (ranked by severity x frequency — "
        "bullet points with explanation tied to specific patterns)"
    )
    lines.append(
        "3. **Training Recommendations** (concrete, actionable — "
        "openings to study, tactics focus, endgame drills)"
    )
    lines.append("4. **Strengths** (patterns that show good play, or absence of negative patterns)")
    lines.append(
        "5. **Next Session Focus** (single most important thing "
        "to work on before next play session)"
    )

    return "\n".join(lines)


def _fallback_report(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
) -> str:
    """Fallback report when LLM is not configured or fails."""
    lines = [
        f"# Coaching Report: {username}",
        "",
        "_LLM coaching unavailable — set LLM_API_KEY in .env for AI-generated analysis._",
        "",
        "## Raw Pipeline Data",
        "",
        f"**Games analyzed:** {games_analyzed}",
        "",
    ]
    if patterns:
        lines.append("### Detected Patterns")
        for p in patterns:
            severity = p.get("severity", "?").upper()
            pid = p.get("pattern_id", "?")
            name = p.get("pattern_name", "?")
            conf = p.get("confidence", "?")
            lines.append(f"- **[{severity}] {pid}: {name}** — confidence {conf}%")
            hypothesis = p.get("hypothesis")
            if hypothesis:
                lines.append(f"  -> {hypothesis}")
        lines.append("")
    if weakness_report:
        lines.append("### Weakness Report")
        acpl = weakness_report.get("total_acpl")
        if acpl is not None:
            lines.append(f"- ACPL: {acpl}")
        lines.append("")
    lines.append("---")
    lines.append("*To enable LLM coaching: add LLM_API_KEY to .env*")
    return "\n".join(lines)


def generate_coaching_report(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
) -> str:
    """Generate a human-readable coaching report from deterministic pipeline data.

    Uses LLM if configured (LLM_API_KEY env var), otherwise returns
    a formatted dump of the raw pipeline data.
    """
    if not LLM_API_KEY:
        return _fallback_report(username, games_analyzed, patterns, weakness_report)

    user_prompt = _build_coaching_prompt(username, games_analyzed, patterns, weakness_report)
    result = _call_llm(COACHING_SYSTEM_PROMPT, user_prompt)
    if result and result.startswith("[LLM error"):
        return _fallback_report(username, games_analyzed, patterns, weakness_report)
    return result or _fallback_report(username, games_analyzed, patterns, weakness_report)


def is_llm_available() -> bool:
    """Check if LLM API key is configured."""
    return bool(LLM_API_KEY)
