"""P0-9: the pinned engine identity fixture is structurally valid and exact."""

import importlib.util
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG = os.path.join(ROOT, "config", "engine_identity.json")
SCRIPT = os.path.join(ROOT, "scripts", "verify_engine_identity.py")

_spec = importlib.util.spec_from_file_location("verify_engine_identity", SCRIPT)
verifier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verifier)


def test_config_pins_a_release_name_and_both_hashes():
    cfg = verifier.load_config()
    assert cfg["release_tag"] == "sf_18"
    assert cfg["expected_uci_name"] == "Stockfish 18"
    assert cfg["linux_ci"]["asset_name"] == "stockfish-ubuntu-x86-64.tar"
    for key in ("archive_sha256", "binary_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", cfg["linux_ci"][key])
    assert re.fullmatch(r"[0-9a-f]{64}", cfg["local_windows_bmi2"]["sha256"])
    assert cfg["linux_ci"]["url"].endswith(cfg["linux_ci"]["asset_name"])


def test_identity_match_is_exact():
    assert verifier.check_identity("Stockfish 18", "Stockfish 18")
    assert not verifier.check_identity("Stockfish 18.1", "Stockfish 18")
    assert not verifier.check_identity(None, "Stockfish 18")
    assert not verifier.check_identity("", "Stockfish 18")


def test_binary_hash_lookup_is_by_file_name():
    cfg = verifier.load_config()
    from pathlib import Path

    linux = Path(cfg["linux_ci"]["binary_in_archive"])
    windows = Path(cfg["local_windows_bmi2"]["binary"])
    assert verifier.expected_binary_hash(cfg, linux) == cfg["linux_ci"]["binary_sha256"]
    assert verifier.expected_binary_hash(cfg, windows) == cfg["local_windows_bmi2"]["sha256"]
    assert verifier.expected_binary_hash(cfg, Path("other-engine")) is None
