"""P0-9: verify the Stockfish used by the real_engine CI job is the pinned one.

The job downloads a release asset and checks its archive hash; this script adds
the two facts that matter at runtime: the UCI `id name` and the binary SHA-256.
Output is a single JSON line so CI logs carry the provenance.

    python -X utf8 scripts/verify_engine_identity.py [--path PATH] [--config PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import chess.engine

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "engine_identity.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check_identity(actual_name: str | None, expected_name: str) -> bool:
    """Exact match: 'Stockfish 18' must not be accepted as 'Stockfish 18.1'."""
    return bool(actual_name) and actual_name == expected_name


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_binary_hash(config: dict, path: Path) -> str | None:
    """Known hashes by file name; an unknown local build is reported, not trusted."""
    known = {
        Path(config["linux_ci"]["binary_in_archive"]).name: config["linux_ci"]["binary_sha256"],
        Path(config["local_windows_bmi2"]["binary"]).name: config["local_windows_bmi2"]["sha256"],
    }
    return known.get(path.name)


def _resolve(raw: str) -> Path | None:
    candidate = Path(raw)
    if candidate.parent != Path("."):
        return candidate if candidate.is_file() else None
    found = shutil.which(raw)
    return Path(found) if found else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=os.environ.get("STOCKFISH_PATH", "stockfish"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)

    config = load_config(args.config)
    path = _resolve(args.path)
    if path is None:
        print(json.dumps({"error": f"stockfish binary not found: {args.path}"}))
        return 2

    binary_hash = sha256_of(path)
    wanted_hash = expected_binary_hash(config, path)
    hash_ok = wanted_hash is None or binary_hash == wanted_hash

    try:
        engine = chess.engine.SimpleEngine.popen_uci(str(path))
        try:
            actual_name = str(engine.id.get("name") or "")
        finally:
            engine.quit()
    except Exception as exc:  # UCI handshake failure is a hard CI failure.
        print(json.dumps({"error": f"UCI handshake failed: {exc}", "path": str(path)}))
        return 2

    name_ok = check_identity(actual_name, config["expected_uci_name"])
    report = {
        "release_tag": config["release_tag"],
        "binary": path.name,
        "binary_sha256": binary_hash,
        "expected_binary_sha256": wanted_hash,
        "hash_ok": hash_ok,
        "uci_name": actual_name,
        "expected_uci_name": config["expected_uci_name"],
        "name_ok": name_ok,
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if hash_ok and name_ok else 1


if __name__ == "__main__":
    sys.exit(main())
