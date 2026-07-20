"""Generate a minimal valid Stockfish cache file for CI contract tests.

Creates data/game_cache/_ci_dummy_d12.json with the exact schema
that _build_game_prompt() and contract tests expect.
"""

import json, os

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
os.makedirs(BASE, exist_ok=True)

dummy = {
    "game": {
        "id": "ci_dummy",
        "color": "white",
        "result": "1-0",
        "opening": "Italian Game",
        "opponent_name": "CI Bot",
        "opponent_rating": 1500,
    },
    "moves": [
        {
            "ply": 1,
            "move_san": "e4",
            "centipawn_loss": 0,
            "phase": "opening",
            "accuracy": 99.0,
        },
        {
            "ply": 2,
            "move_san": "e5",
            "centipawn_loss": 0,
            "phase": "opening",
            "accuracy": 99.0,
        },
        {
            "ply": 3,
            "move_san": "Nf3",
            "centipawn_loss": 10,
            "phase": "opening",
            "accuracy": 97.0,
        },
        {
            "ply": 4,
            "move_san": "Nc6",
            "centipawn_loss": 5,
            "phase": "opening",
            "accuracy": 98.0,
        },
        {
            "ply": 20,
            "move_san": "Qxf7",
            "centipawn_loss": 300,
            "phase": "middlegame",
            "accuracy": 30.0,
        },
        {
            "ply": 21,
            "move_san": "Kxf7",
            "centipawn_loss": 0,
            "phase": "middlegame",
            "accuracy": 99.0,
        },
    ],
    "blunders": [
        {"ply": 20, "move_san": "Qxf7", "centipawn_loss": 300, "phase": "middlegame"}
    ],
    "mistakes": [
        {"ply": 3, "move_san": "Nf3", "centipawn_loss": 10, "phase": "opening"}
    ],
    "inaccuracies": [],
    "phase_stats": {
        "opening": {
            "acpl": 5,
            "accuracy": 98.0,
            "move_count": 2,
            "errors": 0,
        },
        "middlegame": {
            "acpl": 150,
            "accuracy": 64.5,
            "move_count": 2,
            "errors": 1,
        },
        "endgame": {
            "acpl": 0,
            "accuracy": 0.0,
            "move_count": 0,
            "errors": 0,
        },
    },
    "total_acpl": 52,
    "accuracy": 81.0,
}

path = os.path.join(BASE, "_ci_dummy_d12.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(dummy, f, indent=2, ensure_ascii=False)
print(f"Created {path}")
print(
    f"  game: {dummy['game']['id']}, {len(dummy['moves'])} moves, {len(dummy['blunders'])} blunders, {len(dummy['mistakes'])} mistakes"
)
print(f"  total_acpl: {dummy['total_acpl']}, accuracy: {dummy['accuracy']}%")
