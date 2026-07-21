"""B2B-Knowledge-Base persistence layer."""

import json
import os
from datetime import datetime

KB_ROOT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "B2B-Knowledge-Base",
)

ANALYSIS_DIR = os.path.join(KB_ROOT, "02_ANAL\xddZY", "02_chess")
PATTERN_DIR = os.path.join(KB_ROOT, "04_KNOWLEDGE_BASE", "02_chess")


def _ensure_dirs():
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    os.makedirs(PATTERN_DIR, exist_ok=True)


def write_analysis_report(username: str, report: dict) -> str:
    _ensure_dirs()
    date = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"chess_diagnosis_{username}_{date}.md"
    path = os.path.join(ANALYSIS_DIR, filename)
    lines = [
        f"# Diagnoza: {username} ({date})",
        "",
        "## Prehled",
        f"- Analyzovano her: {report.get('games_analyzed', 0)}",
        f"- Celkovy ACPL: {report.get('total_acpl', 0):.1f}",
        f"- Chyb: {report.get('blunders', 0)} blatantnich + {report.get('mistakes', 0)} chyb + {report.get('inaccuracies', 0)} nepresnosti",
        "",
    ]
    if report.get("phase_weaknesses"):
        lines.append("## Fazove slabiny")
        for phase, stats in report["phase_weaknesses"].items():
            lines.append(
                f"- {phase}: ACPL {stats.get('acpl', 0):.1f}, {stats.get('blunders', 0)} chyb"
            )
        lines.append("")
    if report.get("leaky_openings"):
        lines.append("## Unikajici otvoreni")
        for op in report["leaky_openings"]:
            lines.append(
                f"- {op.get('name', '?')}: {op.get('games', 0)} her, {op.get('blunders', 0)} chyb"
            )
        lines.append("")
    if report.get("top_weaknesses"):
        lines.append("## Hlavni nedostatky")
        for w in report["top_weaknesses"]:
            lines.append(f"- {w}")
        lines.append("")
    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def write_pattern_report(username: str, patterns: list[dict]) -> str:
    _ensure_dirs()
    date = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"player_patterns_{username}_{date}.json"
    path = os.path.join(PATTERN_DIR, filename)
    data = {
        "username": username,
        "date": date,
        "patterns": patterns,
        "total": len(patterns),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
