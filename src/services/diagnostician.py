"""Cross-game weakness diagnosis."""

from src.models.analysis import WeaknessReport
from src.models.game import GameAnalysis
from src.models.pattern import PatternMatch


def diagnose(analyses: list[GameAnalysis], username: str) -> WeaknessReport:
    report = WeaknessReport(username=username, total_games_analyzed=len(analyses))
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    phase_blunders = {"opening": 0, "middlegame": 0, "endgame": 0}
    phase_acpl = {"opening": [], "middlegame": [], "endgame": []}
    total_acpl_sum = 0.0
    move_count = 0
    openings = {}
    pattern_counts = {}
    for analysis in analyses:
        total_blunders += len(analysis.blunders)
        total_mistakes += len(analysis.mistakes)
        total_inaccuracies += len(analysis.inaccuracies)
        for m in analysis.moves:
            total_acpl_sum += m.centipawn_loss
            move_count += 1
            phase_acpl[m.phase].append(m.centipawn_loss)
            if m.classification in ("blunder", "mistake"):
                phase_blunders[m.phase] += 1
        opening_name = analysis.game.opening
        if opening_name:
            if opening_name not in openings:
                openings[opening_name] = {"games": 0, "blunders": 0}
            openings[opening_name]["games"] += 1
            openings[opening_name]["blunders"] += len(analysis.blunders) + len(analysis.mistakes)
    report.blunder_count = total_blunders
    report.mistake_count = total_mistakes
    report.inaccuracy_count = total_inaccuracies
    if move_count > 0:
        report.total_acpl = total_acpl_sum / move_count
    for phase, acpl_list in phase_acpl.items():
        if acpl_list:
            report.phase_weaknesses[phase] = {
                "acpl": sum(acpl_list) / len(acpl_list),
                "blunders": phase_blunders[phase],
                "move_count": len(acpl_list),
            }
    for name, data in sorted(openings.items(), key=lambda x: x[1]["blunders"], reverse=True)[:5]:
        report.leaky_openings.append(
            {
                "name": name,
                "games": data["games"],
                "blunders": data["blunders"],
            }
        )
    if phase_blunders["middlegame"] >= phase_blunders["opening"] + phase_blunders["endgame"]:
        report.top_weaknesses.append("Tactical awareness in middlegame transitions")
    if report.total_acpl > 80:
        report.top_weaknesses.append("Overall precision: high centipawn loss")
    if openings and list(openings.values())[0]["blunders"] > 2:
        report.top_weaknesses.append(f"Opening preparation: {list(openings.keys())[0]}")
    return report
