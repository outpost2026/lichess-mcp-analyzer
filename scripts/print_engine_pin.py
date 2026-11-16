"""Print the pinned Stockfish asset metadata as GitHub Actions outputs.

    uv run python scripts/print_engine_pin.py --output "$GITHUB_OUTPUT"

One Python process (no nested shell quoting) is the single reader of
`config/engine_identity.json` in CI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from verify_engine_identity import load_config

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "engine_identity.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    pin = load_config(CONFIG)["linux_ci"]
    lines = [
        f"url={pin['url']}",
        f"archive_sha={pin['archive_sha256']}",
        f"binary={pin['binary_in_archive']}",
        f"binary_sha={pin['binary_sha256']}",
    ]
    text = "\n".join(lines) + "\n"
    if args.output:
        with open(args.output, "a", encoding="utf-8") as handle:
            handle.write(text)
    print(text, end="")


if __name__ == "__main__":
    main()
