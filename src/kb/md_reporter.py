"""MD report generator for coaching pipeline output."""

import os
from datetime import datetime, timezone
from typing import Optional


def generate_md_report(
    username: str,
    games_data: list[dict],
    analyses_data: list[dict],
    pattern_results: list[dict],
    weakness_report: Optional[dict],
    llm_report: str,
    cascade_log: list[dict],
    timing: dict,
    anomalies: list[dict],
) -> str:
    """Generate a human-readable Markdown coaching report."""

    lines = [
        f"# Coaching Report: {username}",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Pipeline:** deterministic (Stockfish) + LLM reasoning",
        f"**Data source:** Lichess API + local cache",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- **Games fetched:** {games_data.get('total', 0)} ({games_data.get('new', 0)} new, {games_data.get('cached', 0)} from cache)",
        f"- **Games analyzed:** {analyses_data.get('analyzed', 0)}",
        f"- **Patterns detected:** {len(pattern_results)}",
        f"- **LLM provider:** {cascade_log[-1].get('provider', 'N/A') if cascade_log else 'N/A'}",
        f"- **Pipeline time:** {timing.get('total', {}).get('duration', 0):.1f}s",
        "",
    ]

    # Timing breakdown
    if timing:
        lines.append("### Pipeline timing")
        lines.append("")
        lines.append("| Phase | Time | % of total |")
        lines.append("|-------|------|-----------|")
        for phase, data in sorted(
            timing.items(), key=lambda x: x[1].get("duration", 0), reverse=True
        ):
            if phase == "total":
                continue
            dur = data.get("duration", 0)
            total_dur = timing.get("total", {}).get("duration", 1)
            pct = dur / total_dur * 100 if total_dur > 0 else 0
            label = data.get("label", phase)
            lines.append(f"| {label} | {dur:.1f}s | {pct:.0f}% |")
        lines.append("")

    # Games analyzed
    if analyses_data.get("games"):
        lines.append("### Games analyzed")
        lines.append("")
        lines.append("| Game | Color | Opening | Result | ACPL | Blunders | Moves | Source |")
        lines.append("|------|-------|---------|--------|------|----------|-------|--------|")
        for g in analyses_data["games"]:
            src = "cache" if g.get("from_cache") else "API"
            lines.append(
                f"| {g.get('id', '?')} | {g.get('color', '?')} | {g.get('opening', '?')} | "
                f"{g.get('result', '?')} | {g.get('acpl', '?')} | {g.get('blunders', '?')} | "
                f"{g.get('moves', '?')} | {src} |"
            )
        lines.append("")

    # Pattern detection
    if pattern_results:
        lines.append("### Detected Patterns")
        lines.append("")
        lines.append("| Pattern | Name | Confidence | Frequency | Severity |")
        lines.append("|---------|------|------------|-----------|----------|")
        for p in sorted(
            pattern_results,
            key=lambda x: (x.get("severity", "low") != "critical", -x.get("confidence", 0)),
        ):
            lines.append(
                f"| {p.get('pattern_id', '?')} | {p.get('pattern_name', '?')} | "
                f"{p.get('confidence', '?')}% | {p.get('frequency', '?')} | "
                f"{p.get('severity', '?').upper()} |"
            )
        lines.append("")

        # Evidence details for critical/high patterns
        high_patterns = [p for p in pattern_results if p.get("severity") in ("critical", "high")]
        if high_patterns:
            lines.append("#### High-severity pattern details")
            lines.append("")
            for p in high_patterns:
                lines.append(f"**{p.get('pattern_id')}: {p.get('pattern_name')}**")
                if p.get("hypothesis"):
                    lines.append(f"- *Hypothesis:* {p['hypothesis']}")
                if p.get("mitigation"):
                    lines.append(f"- *Mitigation:* {p['mitigation']}")
                if p.get("compression_ratio"):
                    lines.append(f"- *Compression ratio:* {p['compression_ratio']:.1f}")
                lines.append("")
    else:
        lines.append("*No patterns detected (sample too small or thresholds not met).*")
        lines.append("")

    # Weakness report
    if weakness_report:
        lines.append("### Weakness Report")
        lines.append("")
        lines.append(f"- **Total ACPL:** {weakness_report.get('total_acpl', '?')}")
        lines.append(f"- **Blunders:** {weakness_report.get('blunder_count', '?')}")
        lines.append(f"- **Mistakes:** {weakness_report.get('mistake_count', '?')}")
        lines.append(f"- **Inaccuracies:** {weakness_report.get('inaccuracy_count', '?')}")
        lines.append("")

        pw = weakness_report.get("phase_weaknesses")
        if pw:
            lines.append("#### Phase breakdown")
            lines.append("")
            lines.append("| Phase | ACPL | Blunders |")
            lines.append("|-------|------|----------|")
            for phase, stats in pw.items():
                lines.append(
                    f"| {phase} | {stats.get('acpl', '?'):.1f} | {stats.get('blunders', '?')} |"
                )
            lines.append("")

        leaky = weakness_report.get("leaky_openings")
        if leaky:
            lines.append("#### Leaky openings")
            lines.append("")
            lines.append("| Opening | Games | Blunders |")
            lines.append("|---------|-------|----------|")
            for o in leaky:
                lines.append(
                    f"| {o.get('name', '?')} | {o.get('games', '?')} | {o.get('blunders', '?')} |"
                )
            lines.append("")

        tw = weakness_report.get("top_weaknesses")
        if tw:
            lines.append("#### Top weaknesses")
            for w in tw:
                lines.append(f"- {w}")
            lines.append("")

    # LLM Coaching
    lines.append("---")
    lines.append("## LLM Coaching Report")
    lines.append("")

    # Cascade log
    if cascade_log:
        lines.append("### Provider cascade")
        lines.append("")
        lines.append("| # | Provider | Status | Tokens | Cost |")
        lines.append("|---|----------|--------|--------|------|")
        for i, att in enumerate(cascade_log):
            prov = att.get("provider", "?")
            error = att.get("error")
            tokens = att.get("total_tokens", att.get("estimated_input_tokens", "?"))
            cost = att.get("cost_usd", 0)
            if error:
                lines.append(f"| {i + 1} | {prov} | ❌ {error[:60]} | - | - |")
            else:
                lines.append(f"| {i + 1} | {prov} | ✅ OK | {tokens} | ${cost:.6f} |")
        lines.append("")

    # The actual LLM report
    lines.append(llm_report)

    # Anomalies
    if anomalies:
        lines.append("")
        lines.append("---")
        lines.append("## Anomalies & Warnings")
        lines.append("")
        lines.append("| Severity | Source | Message |")
        lines.append("|----------|--------|---------|")
        for a in anomalies:
            lines.append(
                f"| {a.get('severity', '?')} | {a.get('source', '?')} | {a.get('msg', a.get('message', '?'))} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_md_report(report: str, username: str, docs_dir: Optional[str] = None) -> str:
    """Write MD report to ./docs and return file path."""
    if docs_dir is None:
        docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs")

    os.makedirs(docs_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"coaching_report_{username}_{ts}.md"
    filepath = os.path.join(docs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return filepath
