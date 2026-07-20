"""Contract tests: Stockfish cache data ↔ LLM prompt key mapping.

These tests verify the contract between modules:
- Producer: GameAnalysis → Stockfish JSON cache (game_cache/*.json)
- Consumer: _build_game_prompt() → reads specific keys from that JSON

If the model keys change, these tests fail — preventing silent "?" in LLM output.
"""

import os, sys, json, glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")


# ── Helper: find a real cache file ──────────────────────────────────────────


def _find_cache_files():
    return sorted(glob.glob(os.path.join(CACHE_DIR, "*_d*.json")))


def _first_cache() -> dict:
    files = _find_cache_files()
    assert files, f"No Stockfish cache files found in {CACHE_DIR}"
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


# ── KEYS THAT _build_game_prompt() READS ────────────────────────────────────
# These are the exact keys used in src/services/game_llm_cache.py:_build_game_prompt()
# If you change key names in the GameAnalysis model, update this list.

PROMPT_TOP_LEVEL_KEYS = {
    "game": dict,  # sub-dict
    "moves": list,
    "blunders": list,
    "mistakes": list,
    "inaccuracies": list,
    "phase_stats": dict,
}

PROMPT_GAME_SUBKEYS = {"id", "color", "result", "opening", "opponent_name", "opponent_rating"}

PROMPT_ERROR_SUBKEYS = {"ply", "move_san", "centipawn_loss", "phase"}

PROMPT_PHASE_STATS_EXPECTED = {"opening", "middlegame", "endgame"}
PROMPT_PHASE_STATS_SUBKEYS = {"acpl", "accuracy", "move_count", "errors"}


class TestStockfishCacheContract:
    """Verify Stockfish cache files contain all keys that the LLM prompt reads."""

    def test_cache_files_exist(self):
        files = _find_cache_files()
        assert len(files) > 0, (
            f"No Stockfish cache files in {CACHE_DIR}. Run the analysis pipeline first."
        )

    def test_top_level_keys(self):
        data = _first_cache()
        for key, expected_type in PROMPT_TOP_LEVEL_KEYS.items():
            assert key in data, (
                f"Missing top-level key '{key}' in cache. "
                f"Prompt reads it as data.get('{key}', ...). "
                f"Available keys: {list(data.keys())}"
            )
            assert isinstance(data[key], expected_type), (
                f"Key '{key}' should be {expected_type.__name__}, got {type(data[key]).__name__}"
            )

    def test_game_subkeys(self):
        data = _first_cache()
        game = data.get("game", {})
        for key in PROMPT_GAME_SUBKEYS:
            assert key in game, (
                f"Missing game subkey '{key}'. "
                f"Prompt reads it as game.get('{key}', '?'). "
                f"Available game keys: {list(game.keys())}"
            )

    def test_blunder_subkeys(self):
        data = _first_cache()
        blunders = data.get("blunders", [])
        if not blunders:
            return  # no blunders in this game
        for key in PROMPT_ERROR_SUBKEYS:
            assert key in blunders[0], (
                f"Missing blunder key '{key}'. "
                f"Prompt reads it as b.get('{key}', '?'). "
                f"Available blunder keys: {list(blunders[0].keys())}"
            )

    def test_mistake_subkeys(self):
        data = _first_cache()
        mistakes = data.get("mistakes", [])
        if not mistakes:
            return
        for key in PROMPT_ERROR_SUBKEYS:
            assert key in mistakes[0], (
                f"Missing mistake key '{key}'. Available keys: {list(mistakes[0].keys())}"
            )

    def test_inaccuracy_subkeys(self):
        data = _first_cache()
        inaccs = data.get("inaccuracies", [])
        if not inaccs:
            return
        for key in PROMPT_ERROR_SUBKEYS:
            assert key in inaccs[0], (
                f"Missing inaccuracy key '{key}'. Available keys: {list(inaccs[0].keys())}"
            )

    def test_accuracy_not_zero(self):
        data = _first_cache()
        acc = data.get("accuracy", 0.0)
        assert acc != 0.0, (
            f"Accuracy is 0.0 — this is a data bug. "
            f"ACPL is {data.get('total_acpl', '?')}. "
            f"auto_annotate() should compute accuracy from moves."
        )

    def test_phase_stats_populated(self):
        data = _first_cache()
        ps = data.get("phase_stats", {})
        assert ps, f"phase_stats is empty — auto_annotate() should populate it. Available: {ps}"
        for phase in PROMPT_PHASE_STATS_EXPECTED:
            if phase in ps:
                for subkey in PROMPT_PHASE_STATS_SUBKEYS:
                    assert subkey in ps[phase], (
                        f"Missing phase_stats.{phase}.{subkey}. Available: {list(ps[phase].keys())}"
                    )


class TestPromptNoPlaceholders:
    """Verify the built prompt contains real values, not '?'."""

    def _build_prompt_for_first_cache(self) -> str:
        from src.services.game_llm_cache import _build_game_prompt

        data = _first_cache()
        return _build_game_prompt(data)

    def test_prompt_has_no_unknown_move(self):
        prompt = self._build_prompt_for_first_cache()
        lines = prompt.split("\n")
        error_lines = [l for l in lines if l.startswith(("BLUNDER:", "MISTAKE:", "INACC:"))]
        for line in error_lines:
            assert "?" not in line, (
                f"Prompt contains '?' in error line: {line}. "
                f"This means a key name in _build_game_prompt() doesn't match the data."
            )

    def test_prompt_has_no_zero_accuracy(self):
        prompt = self._build_prompt_for_first_cache()
        for line in prompt.split("\n"):
            if "Accuracy:" in line and "0.0%" in line:
                # Could be legit if total_acpl is very high, but flag it
                data = _first_cache()
                acpl = data.get("total_acpl", 0)
                assert acpl > 200, (
                    f"Accuracy shows 0.0% but ACPL is only {acpl}. "
                    f"auto_annotate() may not have recomputed accuracy yet."
                )

    def test_prompt_contains_phase_data(self):
        prompt = self._build_prompt_for_first_cache()
        has_phase = any("Phase breakdown" in l for l in prompt.split("\n"))
        data = _first_cache()
        ps = data.get("phase_stats", {})
        if ps:
            assert has_phase, (
                f"phase_stats has data ({len(ps)} phases) but prompt doesn't show 'Phase breakdown'. "
                f"Check _build_game_prompt() phase_stats rendering."
            )


class TestAccuracyComputation:
    """Verify accuracy is computed reasonably for all cache files."""

    def test_all_caches_have_reasonable_accuracy(self):
        files = _find_cache_files()
        assert files, "No cache files"
        bad = []
        for path in files:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            acc = data.get("accuracy", 0.0)
            acpl = data.get("total_acpl", 0)
            if acc == 0.0 and acpl < 100:
                bad.append((os.path.basename(path), acc, acpl))
        assert not bad, (
            f"Caches with accuracy=0.0 but low ACPL: {bad}. "
            f"Expected auto_annotate() to compute accuracy."
        )


class TestGameAnalysisModelContract:
    """Verify GameAnalysis model keys match what prompt builder expects."""

    def test_to_dict_keys_match_prompt_keys(self):
        # Use GameAnalysis.to_dict() output and check prompt-readable keys
        from src.models.game import GameSummary, GameAnalysis

        g = GameSummary(
            id="test",
            platform="lichess",
            opening="",
            opening_eco="",
            color="white",
            result="1-0",
            opponent_name="opp",
            opponent_rating=1500,
            player_rating=1500,
            time_control="",
            date="",
            url="",
        )
        a = GameAnalysis(game=g)
        d = a.to_dict()

        for key in PROMPT_TOP_LEVEL_KEYS:
            assert key in d, (
                f"GameAnalysis.to_dict() missing key '{key}' used by prompt. "
                f"Available: {list(d.keys())}"
            )
