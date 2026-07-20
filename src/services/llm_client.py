"""LLM reasoning layer for coaching report generation.

Transforms deterministic pipeline output (PatternMatch[], WeaknessReport)
into human-readable coaching analysis. Never invents evidence — only
interprets existing data. Falls back to raw data dump when LLM unavailable.

Supports multiple LLM providers with cascade fallback.
Cascade order: NVIDIA (free) -> Cerebras (free) -> DeepSeek (paid credits).
Token usage is tracked per call.
"""

import os
import json
from typing import Optional

# ── Provider cascade configuration ────────────────────────────────────────
# Order matters: first provider with valid API key is tried first.
# If it fails, cascade to next.

PROVIDERS = [
    {
        "name": "NVIDIA",
        "api_key_var": "NVIDIA_API_KEY",
        "model_var": "NVIDIA_MODEL",
        "default_model": "nvidia/nemotron-3-super-120b-a12b",
        "base_url": "https://api.nvidia.com/v1",
    },
    {
        "name": "Cerebras",
        "api_key_var": "CEREBRAS_API_KEY",
        "model_var": "CEREBRAS_MODEL",
        "default_model": "cerebras/llama3.1-8b",
        "base_url": "https://api.cerebras.ai/v1",
    },
    {
        "name": "DeepSeek",
        "api_key_var": "DEEPSEEK_API_KEY",
        "model_var": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
    },
]

LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))


def list_available_providers() -> list[dict]:
    """Return list of providers that have API keys configured."""
    available = []
    for prov in PROVIDERS:
        key = os.environ.get(prov["api_key_var"], "")
        if key:
            model = os.environ.get(prov["model_var"], prov["default_model"])
            available.append(
                {
                    "provider": prov["name"],
                    "model": model,
                    "key_set": True,
                }
            )
    return available


# ── LLM call with token tracking ──────────────────────────────────────────


def _call_llm(
    system_prompt: str,
    user_prompt: str,
    provider_config: dict,
) -> tuple[Optional[str], dict]:
    """Call a specific LLM provider and return (content, token_log).

    token_log contains:
      - provider: provider name
      - model: model name
      - prompt_tokens: input token count (from API response or estimated)
      - completion_tokens: output token count
      - total_tokens: sum
      - input_chars: len(user_prompt) for debugging
      - output_chars: len(content) for debugging
      - error: error message if failed
    """
    import httpx

    api_key = os.environ.get(provider_config["api_key_var"], "")
    model = os.environ.get(provider_config["model_var"], provider_config["default_model"])
    base_url = provider_config["base_url"]
    provider_name = provider_config["name"]

    token_log = {
        "provider": provider_name,
        "model": model,
        "input_chars": len(user_prompt) + len(system_prompt),
        "error": None,
    }

    if not api_key:
        token_log["error"] = "No API key configured"
        return None, token_log

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Rough token estimation (chars / 4)
    estimated_input_tokens = (len(system_prompt) + len(user_prompt)) // 4
    token_log["estimated_input_tokens"] = estimated_input_tokens

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0,
        )

        # Log HTTP status even if not 200
        token_log["http_status"] = resp.status_code

        if resp.status_code == 401:
            token_log["error"] = f"Unauthorized (401) — check API key for {provider_name}"
            return None, token_log
        if resp.status_code == 402:
            token_log["error"] = f"Payment required (402) — {provider_name} credits exhausted"
            return None, token_log
        if resp.status_code == 429:
            token_log["error"] = f"Rate limited (429) — {provider_name} quota exceeded"
            return None, token_log

        resp.raise_for_status()
        data = resp.json()

        # Extract usage if available
        usage = data.get("usage", {})
        if usage:
            token_log["prompt_tokens"] = usage.get("prompt_tokens", 0)
            token_log["completion_tokens"] = usage.get("completion_tokens", 0)
            token_log["total_tokens"] = usage.get("total_tokens", 0)

        # Extract content
        content = None
        if "choices" in data and len(data["choices"]) > 0:
            content = data["choices"][0]["message"]["content"]
        elif "content" in data and len(data.get("content", [])) > 0:
            content = data["content"][0]["text"]
        else:
            content = str(data)

        if content:
            token_log["output_chars"] = len(content)
            if not token_log.get("completion_tokens"):
                token_log["completion_tokens"] = len(content) // 4
                token_log["total_tokens"] = (
                    token_log.get("estimated_input_tokens", 0) + token_log["completion_tokens"]
                )

        return content, token_log

    except httpx.TimeoutException as e:
        token_log["error"] = f"Timeout: {e}"
        return None, token_log
    except Exception as e:
        token_log["error"] = f"{type(e).__name__}: {e}"
        return None, token_log


# ── Coaching prompt ────────────────────────────────────────────────────────

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


# ── Fallback ───────────────────────────────────────────────────────────────


def _fallback_report(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
) -> str:
    lines = [
        f"# Coaching Report: {username}",
        "",
        "_LLM coaching unavailable after cascade fallback._",
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
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────


def generate_coaching_report_with_logs(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
    cascade_order: Optional[list[str]] = None,
) -> tuple[str, list[dict]]:
    """Generate coaching report with token logging and provider cascade.

    Tries providers in cascade_order (default: NVIDIA -> Cerebras -> DeepSeek).
    Returns (report_text, cascade_log) where cascade_log is a list of
    per-provider attempt logs with token usage.

    Args:
        username: Player's Lichess username
        games_analyzed: Number of games analyzed
        patterns: List of PatternMatch dicts from pipeline
        weakness_report: Optional WeaknessReport dict
        cascade_order: List of provider names to try (e.g. ["NVIDIA", "Cerebras", "DeepSeek"])
                       If None, uses all configured providers in defined order.
    """
    if cascade_order is None:
        cascade_order = ["NVIDIA", "Cerebras", "DeepSeek"]

    user_prompt = _build_coaching_prompt(username, games_analyzed, patterns, weakness_report)
    cascade_log = []

    for order_name in cascade_order:
        provider_config = next((p for p in PROVIDERS if p["name"] == order_name), None)
        if not provider_config:
            cascade_log.append(
                {
                    "provider": order_name,
                    "skipped": True,
                    "error": f"Unknown provider in config",
                }
            )
            continue

        api_key = os.environ.get(provider_config["api_key_var"], "")
        if not api_key:
            cascade_log.append(
                {
                    "provider": order_name,
                    "skipped": True,
                    "error": "No API key configured",
                }
            )
            continue

        content, token_log = _call_llm(COACHING_SYSTEM_PROMPT, user_prompt, provider_config)
        cascade_log.append(token_log)

        if content is not None:
            return content, cascade_log

    # All providers failed
    fallback = _fallback_report(username, games_analyzed, patterns, weakness_report)
    return fallback, cascade_log


def generate_coaching_report(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
) -> str:
    """Simple wrapper — returns just the report text (no logs)."""
    report, _ = generate_coaching_report_with_logs(
        username, games_analyzed, patterns, weakness_report
    )
    return report


def is_llm_available() -> bool:
    """Check if any LLM provider is configured."""
    return any(os.environ.get(p["api_key_var"], "") for p in PROVIDERS)


def get_llm_status() -> dict:
    """Return status info about all configured LLM providers."""
    available = list_available_providers()
    active = None
    for p in PROVIDERS:
        if os.environ.get(p["api_key_var"], ""):
            active = p["name"]
            break
    return {
        "available": available,
        "total_configured": len(available),
        "active_provider": active,
    }
