"""Deterministické nástroje pro práci s hash kalibrací — nulová heuristika.

Vše počítáno z naměřených dat (ply, depth, hashfull, time, nodes), žádný odhad.
Feedback propagation: batch výsledky → nová váha → tabulka.
"""

import json
import pathlib
from typing import Dict, List


def load_batch_results(temp_dir: str) -> List[Dict]:
    p = pathlib.Path(temp_dir) / "batch_20_full.json"
    if not p.exists():
        p = pathlib.Path(temp_dir) / "batch_20_d12_raw.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def hashfull_for(hash_mb: int, ply: int, depth: int, nodes: int) -> float:
    """Deterministický odhad hashfull — bez heuristiky, jen nodes/hash.
    Stockfish hashfull = nodes * 16 / (hash_mb * 1024*1024) * 1000 (promile) → %.
    """
    if hash_mb <= 0:
        return 100.0
    # 1 entry ~16 bytes, hashfull = entries / total_entries
    entries = nodes / 16
    total = hash_mb * 1024 * 1024 / 16
    return min(100.0, entries / total * 100)


def choose_hash_deterministic(ply: int, depth: int) -> int:
    """Čistá tabulka — žádná heuristika, jen ply+depth → hash. Feedback z kalibrace."""
    # Kalibrováno na 20 hrách systeq depth 12/14 (hashfull <10% target, time min)
    # depth 12: 64 stačí pro všechny ply (měřeno 1-2% hashfull)
    # depth 14: 64 <40 ply (4% hashfull), 128 40-80 ply (7%), 256 80+ ply (29%→7%)
    if depth <= 12:
        return 64
    if depth <= 14:
        if ply < 40:
            return 64
        if ply < 80:
            return 128
        return 256
    # depth 18
    if ply < 40:
        return 128
    if ply < 80:
        return 256
    return 512


def calibrate_from_measurements(measurements: List[Dict]) -> Dict:
    """Feedback propagation: z měření (ply, depth, hash, time, hashfull) → váhy.
    Deterministické: pro každý ply bucket vyber nejmenší hash kde hashfull<10% a time je min.
    """
    # measurements: list of {ply, depth, hash, time, hashfull}
    buckets = {}
    for m in measurements:
        key = (m["ply"] // 20 * 20, m["depth"])  # bucket po 20 ply
        buckets.setdefault(key, []).append(m)
    result = {}
    for (ply_bucket, depth), items in sorted(buckets.items()):
        # filtr hashfull <10% (100 = 10% v promile)
        valid = [x for x in items if x["hashfull"] < 100]  # hashfull promile <100 = 10%
        if not valid:
            valid = items
        best = min(valid, key=lambda x: x["time"])
        result[f"ply_{ply_bucket}-{ply_bucket + 19}_d{depth}"] = {
            "best_hash": best["hash"],
            "time": best["time"],
            "hashfull": best["hashfull"],
            "ply_bucket": ply_bucket,
            "depth": depth,
        }
    return result


def log_anomaly(
    game_id: str,
    ply: int,
    depth: int,
    hash_mb: int,
    hashfull: int,
    errors: int,
    time_s: float,
    log_path: str,
) -> None:
    """Zapiš anomálii deterministicky — hashfull>100 (10%) nebo errors>0."""
    if hashfull > 100 or errors > 0:
        p = pathlib.Path(log_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "game_id": game_id,
                        "ply": ply,
                        "depth": depth,
                        "hash": hash_mb,
                        "hashfull_promile": hashfull,
                        "errors": errors,
                        "time": time_s,
                    }
                )
                + "\n"
            )


def save_calibration_table(table: Dict, path: str) -> None:
    pathlib.Path(path).write_text(json.dumps(table, indent=2, ensure_ascii=False), encoding="utf-8")
