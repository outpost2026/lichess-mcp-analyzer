import glob, json, os, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
D = r"C:\Users\PC\Documents\Repozitar_Dev\_github\lichess-analyzer-mcp\data\reports"


def load(game):
    fs = sorted(glob.glob(os.path.join(D, f"single_game_{game}_*.json")))
    if not fs:
        return None, None
    with open(fs[-1], encoding="utf-8") as fh:
        return os.path.basename(fs[-1]), json.load(fh)


def flag(j, side, ply):
    return next((f for f in j[side]["flags"] if f["ply"] == ply), None)


for game in [
    "aFZC293b",
    "DclcmVZy",
    "v2xHpqXG",
    "hcoFhc0a",
    "41Naq3iM",
    "r8dJqFiX",
    "MoP3r6SH",
    "5yM0QRRO",
]:
    name, j = load(game)
    if not j:
        print(game, "MISSING")
        continue
    w, b = j["white"], j["black"]
    print(f"--- {game} {name}")
    print(f"  openings W/B: {w['game'].get('opening')} | {b['game'].get('opening')}")
    print(f"  usernames W/B: {w['game'].get('username')!r} | {b['game'].get('username')!r}")
    print(f"  decisive W: {[x['ply'] for x in w.get('decisive_moves', [])]}")
    print(f"  decisive B: {[x['ply'] for x in b.get('decisive_moves', [])]}")
    for side, ply in [
        ("white", 41),
        ("black", 38),
        ("black", 58),
        ("black", 42),
        ("white", 49),
        ("white", 57),
        ("white", 47),
        ("white", 35),
        ("black", 34),
    ]:
        f = flag(j, side, ply)
        if f:
            print(
                f"  {side} p{ply}: {f.get('move')} cp={f.get('cp')} impact={f.get('game_impact')} mate_missed={f.get('mate_missed')} mate_via={f.get('mate_via')} motif={f.get('motif')} best={f.get('best')}"
            )
