"""LLM reasoning layer for coaching report generation.

Transforms deterministic pipeline output (PatternMatch[], WeaknessReport)
into human-readable coaching analysis. Never invents evidence — only
interprets existing data. Falls back to raw data dump when LLM unavailable.

Supports multiple LLM providers with cascade fallback.
Cascade order: NVIDIA (free) -> Cerebras (free) -> DeepSeek V4 Flash (paid).
DeepSeek Chat je zakázán — příliš drahý ($0.27/$1.10 per 1M toků).
Token usage is tracked per call.
"""

import os
import json
from typing import Optional

# ── Provider cascade configuration ────────────────────────────────────────
# Order matters: first provider with valid API key is tried first.

PROVIDERS = [
    {
        "name": "NVIDIA",
        "api_key_var": "NVIDIA_API_KEY",
        "model_var": "NVIDIA_MODEL",
        "default_model": "nvidia/nemotron-3-super-120b-a12b",
        "base_url": "https://integrate.api.nvidia.com/v1",
    },
    {
        "name": "Cerebras",
        "api_key_var": "CEREBRAS_API_KEY",
        "model_var": "CEREBRAS_MODEL",
        "default_model": "gpt-oss-120b",
        "base_url": "https://api.cerebras.ai/v1",
    },
    {
        "name": "DeepSeek V4 Flash",
        "api_key_var": "DEEPSEEK_API_KEY",
        "model_var": "DEEPSEEK_V4_MODEL",
        "default_model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com/v1",
    },
]

LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "60.0"))


def list_available_providers() -> list[dict]:
    available = []
    for prov in PROVIDERS:
        key = os.environ.get(prov["api_key_var"], "")
        if key:
            model = os.environ.get(prov["model_var"], prov["default_model"])
            available.append({"provider": prov["name"], "model": model, "key_set": True})
    return available


# Provider pricing (USD per 1M tokens) for cost estimation
PROVIDER_PRICING = {
    "NVIDIA": {"input": 0.0, "output": 0.0},  # free tier
    "Cerebras": {"input": 0.0, "output": 0.0},  # free tier
    "DeepSeek Chat": {"input": 0.27, "output": 1.10},
    "DeepSeek V4 Flash": {"input": 0.14, "output": 0.28},
}


def _estimate_cost(provider_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = PROVIDER_PRICING.get(provider_name, {"input": 0, "output": 0})
    return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000


# ── LLM call with token tracking ──────────────────────────────────────────


def _call_llm(
    system_prompt: str, user_prompt: str, provider_config: dict
) -> tuple[Optional[str], dict]:
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

    estimated_input_tokens = len((system_prompt + user_prompt).encode()) // 4
    token_log["estimated_input_tokens"] = estimated_input_tokens

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions", headers=headers, json=payload, timeout=LLM_TIMEOUT
        )
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

        usage = data.get("usage", {})
        if usage:
            token_log["prompt_tokens"] = usage.get("prompt_tokens", 0)
            token_log["completion_tokens"] = usage.get("completion_tokens", 0)
            token_log["total_tokens"] = usage.get("total_tokens", 0)

        content = None
        if "choices" in data and len(data["choices"]) > 0:
            msg = data["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning")
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

        # Cost estimate
        pt = token_log.get("prompt_tokens", token_log.get("estimated_input_tokens", 0))
        ct = token_log.get("completion_tokens", 0)
        token_log["cost_usd"] = round(_estimate_cost(provider_name, pt, ct), 6)

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


def build_coaching_prompt(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
    game_summaries: Optional[list[dict]] = None,
) -> str:
    lines = [
        f"Player: {username}",
        f"Games analyzed: {games_analyzed}",
        "",
    ]

    # Per-game summaries (from Level 2 LLM cache) — lighter than raw data
    if game_summaries:
        lines.append("=== Per-Game LLM Analysis ===")
        for gs in game_summaries:
            gid = gs.get("game_id", "?")
            color = gs.get("color", "?")
            acpl = gs.get("acpl", "?")
            blunders = gs.get("blunders", "?")
            summary = gs.get("llm_summary", "")
            lines.append(f"- {gid} ({color}): ACPL={acpl}, blunders={blunders}")
            if summary:
                lines.append(f"  Analysis: {summary}")
            lines.append("")

    lines.append("=== Pattern Detection Results ===")
    if patterns:
        for p in patterns:
            s = p.get("severity", "?").upper()
            pid = p.get("pattern_id", "?")
            name = p.get("pattern_name", "?")
            conf = p.get("confidence", "?")
            freq = p.get("frequency", "?")
            lines.append(f"- [{s}] {pid}: {name} (confidence: {conf}%, frequency: {freq})")
            h = p.get("hypothesis")
            if h:
                lines.append(f"  Hypothesis: {h}")
            m = p.get("mitigation")
            if m:
                lines.append(f"  Mitigation: {m}")
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
        pw = wr.get("phase_weaknesses")
        if pw:
            lines.append("Phase breakdown:")
            for phase, stats in pw.items():
                lines.append(
                    f"  {phase}: ACPL {stats.get('acpl', '?')}, blunders {stats.get('blunders', '?')}"
                )
        leaky = wr.get("leaky_openings")
        if leaky:
            lines.append("Leaky openings:")
            for o in leaky:
                lines.append(
                    f"  {o.get('name', '?')}: {o.get('games', '?')} games, {o.get('blunders', '?')} blunders"
                )
        tw = wr.get("top_weaknesses")
        if tw:
            lines.append("Top weaknesses:")
            for w in tw:
                lines.append(f"  - {w}")
    lines.append("")
    lines.append("=== INSTRUCTIONS ===")
    lines.append("Produce a coaching report with these sections:")
    lines.append("1. **Summary** (2-3 sentences)")
    lines.append("2. **Priority Issues** (ranked by severity x frequency)")
    lines.append("3. **Training Recommendations** (concrete, actionable)")
    lines.append("4. **Strengths** (patterns that show good play)")
    lines.append("5. **Next Session Focus**")
    return "\n".join(lines)


# ── Fallback ───────────────────────────────────────────────────────────────


def _fallback_report(
    username: str, games_analyzed: int, patterns: list[dict], weakness_report: Optional[dict] = None
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
            s = p.get("severity", "?").upper()
            pid = p.get("pattern_id", "?")
            name = p.get("pattern_name", "?")
            conf = p.get("confidence", "?")
            lines.append(f"- **[{s}] {pid}: {name}** — confidence {conf}%")
            h = p.get("hypothesis")
            if h:
                lines.append(f"  -> {h}")
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
    game_summaries: Optional[list[dict]] = None,
) -> tuple[str, list[dict]]:
    if cascade_order is None:
        default = os.environ.get("DEFAULT_PROVIDER", "").strip().lower()
        if default == "cerebras":
            cascade_order = ["Cerebras", "NVIDIA", "DeepSeek V4 Flash"]
        elif default == "deepseek":
            cascade_order = ["DeepSeek V4 Flash", "NVIDIA", "Cerebras"]
        else:
            cascade_order = ["NVIDIA", "Cerebras", "DeepSeek V4 Flash"]

    user_prompt = build_coaching_prompt(
        username, games_analyzed, patterns, weakness_report, game_summaries
    )
    cascade_log = []

    for order_name in cascade_order:
        provider_config = next((p for p in PROVIDERS if p["name"] == order_name), None)
        if not provider_config:
            cascade_log.append(
                {"provider": order_name, "skipped": True, "error": "Unknown provider"}
            )
            continue
        api_key = os.environ.get(provider_config["api_key_var"], "")
        if not api_key:
            cascade_log.append({"provider": order_name, "skipped": True, "error": "No API key"})
            continue
        content, token_log = _call_llm(COACHING_SYSTEM_PROMPT, user_prompt, provider_config)
        cascade_log.append(token_log)
        if content is not None:
            return content, cascade_log

    fallback = _fallback_report(username, games_analyzed, patterns, weakness_report)
    return fallback, cascade_log


def generate_coaching_report(
    username: str,
    games_analyzed: int,
    patterns: list[dict],
    weakness_report: Optional[dict] = None,
    game_summaries: Optional[list[dict]] = None,
) -> str:
    report, _ = generate_coaching_report_with_logs(
        username,
        games_analyzed,
        patterns,
        weakness_report,
        game_summaries=game_summaries,
    )
    return report


def is_llm_available() -> bool:
    return any(os.environ.get(p["api_key_var"], "") for p in PROVIDERS)


def verify_api_keys() -> list[dict]:
    """Lightweight health check: verify each configured API key with a minimal API call.
    Returns list of {provider, key_set, valid, error}."""
    import httpx

    results = []
    for prov in PROVIDERS:
        key = os.environ.get(prov["api_key_var"], "")
        if not key:
            results.append(
                {"provider": prov["name"], "key_set": False, "valid": False, "error": "No key set"}
            )
            continue
        model = os.environ.get(prov["model_var"], prov["default_model"])
        try:
            resp = httpx.post(
                f"{prov['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
                timeout=10.0,
            )
            if resp.status_code == 200:
                results.append(
                    {"provider": prov["name"], "key_set": True, "valid": True, "error": None}
                )
            elif resp.status_code == 401:
                results.append(
                    {
                        "provider": prov["name"],
                        "key_set": True,
                        "valid": False,
                        "error": "Invalid API key (401)",
                    }
                )
            elif resp.status_code == 402:
                results.append(
                    {
                        "provider": prov["name"],
                        "key_set": True,
                        "valid": False,
                        "error": "Insufficient credits (402)",
                    }
                )
            elif resp.status_code == 429:
                results.append(
                    {
                        "provider": prov["name"],
                        "key_set": True,
                        "valid": True,
                        "error": "Rate limited (429) — key valid but throttled",
                    }
                )
            else:
                results.append(
                    {
                        "provider": prov["name"],
                        "key_set": True,
                        "valid": False,
                        f"error": f"HTTP {resp.status_code}",
                    }
                )
        except httpx.TimeoutException:
            results.append(
                {
                    "provider": prov["name"],
                    "key_set": True,
                    "valid": True,
                    "error": "Timeout — provider unreachable, key assumed valid",
                }
            )
        except Exception as e:
            results.append(
                {
                    "provider": prov["name"],
                    "key_set": True,
                    "valid": False,
                    "error": f"{type(e).__name__}: {e}",
                }
            )
    return results


def get_llm_status() -> dict:
    available = list_available_providers()
    active = None
    for p in PROVIDERS:
        if os.environ.get(p["api_key_var"], ""):
            active = p["name"]
            break
    mode = os.environ.get("PIPELINE_MODE", "auto")
    return {
        "available": available,
        "total_configured": len(available),
        "active_provider": active,
        "pipeline_mode": mode,
    }


# ── Pipeline orchestrator ──────────────────────────────────────────────────


def run_coaching_pipeline(
    username: str,
    game_ids: list[str],
    game_colors: Optional[list[str]] = None,
    patterns: Optional[list[dict]] = None,
    weakness_report: Optional[dict] = None,
    cascade_order: Optional[list[str]] = None,
    mode: str = "auto",
    force_llm_cache: bool = False,
) -> tuple[str, list[dict], dict]:
    """Orchestruje LLM cast pipeline dle zvoleneho rezimu.

    Mode:
      "auto"        — N≤30 → mono, N>30 → incremental
      "mono"        — jeden LLM call s raw daty (monolit)
      "incremental" — per-game LLM cache + aggregate se summaries

    Returns: (report, cascade_log, meta)
      meta = {"mode": str, "games_analyzed": int, "per_game_calls": int, "per_game_tokens": int}
    """
    from lichess_analyzer_mcp.services.game_llm_cache import analyze_game_llm, get_all_game_summaries

    n = len(game_ids)
    env_mode = os.environ.get("PIPELINE_MODE", "").strip().lower()
    effective_mode = (
        mode if mode != "auto" else (env_mode or ("mono" if n <= 30 else "incremental"))
    )

    meta = {"mode": effective_mode, "games_analyzed": n, "per_game_calls": 0, "per_game_tokens": 0}

    if effective_mode == "mono":
        report, log = generate_coaching_report_with_logs(
            username=username,
            games_analyzed=n,
            patterns=patterns or [],
            weakness_report=weakness_report,
            cascade_order=cascade_order,
            game_summaries=None,
        )
        return report, log, meta

    # incremental
    colors = game_colors or ["white"] * n
    per_game_tokens = 0
    for i, gid in enumerate(game_ids):
        result = analyze_game_llm(gid, colors[i], force=force_llm_cache)
        if result and result.get("token_log"):
            per_game_tokens += result["token_log"].get("total_tokens", 0)
        meta["per_game_calls"] += 1

    summaries = get_all_game_summaries(game_ids)
    report, log = generate_coaching_report_with_logs(
        username=username,
        games_analyzed=n,
        patterns=patterns or [],
        weakness_report=weakness_report,
        cascade_order=cascade_order,
        game_summaries=summaries,
    )
    meta["per_game_tokens"] = per_game_tokens
    return report, log, meta
