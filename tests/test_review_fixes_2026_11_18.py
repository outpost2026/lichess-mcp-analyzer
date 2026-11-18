"""Regression tests for the P0/P1 defects found by the 2026-11-18 code review."""

import pytest

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary
from lichess_analyzer_mcp.services import diagnostician, srs_engine


@pytest.mark.asyncio
async def test_opponent_pool_persist_uses_keyword_args(monkeypatch):
    """P0: 2nd positional arg is username, not depth (report_persister.py:249)."""
    import lichess_analyzer_mcp.tools.coaching_opponent_pool as pool_mod
    from lichess_analyzer_mcp.services.report_persister import _run_tool

    captured = {}

    async def fake(game_ids, username="", depth=0, max_seconds=0):
        captured.update(game_ids=game_ids, username=username, depth=depth)
        return {"ok": True, "cascade_log": []}

    monkeypatch.setattr(pool_mod, "lichess_coaching_opponent_pool", fake)
    await _run_tool(
        "opponent_pool", {"game_ids": ["abc12345", "def67890"], "username": "u", "depth": 12}
    )
    assert captured == {"game_ids": "abc12345,def67890", "username": "u", "depth": 12}


def test_srs_retention_rate_survives_reload(monkeypatch, tmp_path):
    """P1: _load() dropped retention_rate, collapsing the running mean."""
    path = tmp_path / "srs_cards.json"
    monkeypatch.setattr(srs_engine, "SRS_FILE", str(path))
    monkeypatch.setattr(srs_engine, "DATA_DIR", str(tmp_path))

    first = srs_engine.SRSEngine()
    first.state.total_reviews = 4
    first.state.retention_rate = 0.75
    first._save()

    second = srs_engine.SRSEngine()
    assert second.state.retention_rate == 0.75
    assert second.state.total_reviews == 4


def _analysis(opening: str, blunders: int) -> GameAnalysis:
    a = GameAnalysis(
        game=GameSummary(
            id="x",
            platform="lichess",
            opening=opening,
            color="white",
            result="*",
            opening_eco="",
        )
    )
    a.blunders = [object()] * blunders
    a.mistakes = []
    a.moves = []
    return a


def test_worst_opening_uses_blunders_not_games():
    """P1: 'worst opening' was sorted by games (most played), not blunders."""
    analyses = [
        _analysis("Sicilian", 0),
        _analysis("Sicilian", 0),
        _analysis("Sicilian", 0),
        _analysis("Caro-Kann", 3),
        _analysis("Caro-Kann", 3),
        _analysis("Caro-Kann", 3),
    ]
    report = diagnostician.diagnose(analyses, "tester")
    assert any("Caro-Kann" in w for w in report.top_weaknesses)
    assert not any("Sicilian" in w for w in report.top_weaknesses)


@pytest.mark.asyncio
async def test_workspace_info_uses_live_registry():
    """P1: no stale 10-tool fallback / private FastMCP internals."""
    import lichess_analyzer_mcp.server  # noqa: F401 - registers all 18 tools
    from lichess_analyzer_mcp.tools.workspace_info import lichess_workspace_info

    info = await lichess_workspace_info()
    assert info["tools_total"] == 18
    assert len(info["tools"]) == 18
    assert "lichess_persist_report" in info["tools"]


@pytest.mark.asyncio
async def test_audit_detects_status_error_envelope(monkeypatch):
    """P1: {status:'error', errors:[...]} was audited as ok=True."""
    from lichess_analyzer_mcp.services import audit as audit_mod

    entries = []
    monkeypatch.setattr(audit_mod, "_write_entry", lambda e: entries.append(e))

    @audit_mod.auditable
    async def failing_tool():
        return {"status": "error", "errors": ["boom"]}

    await failing_tool()
    assert len(entries) == 1
    assert entries[0]["ok"] is False


def test_anonymous_session_rejects_path_outside_workspace():
    """P1: MCP file_path must not read arbitrary host files."""
    from lichess_analyzer_mcp.tools.anonymous_session import _parse_game_entries

    with pytest.raises(ValueError, match="outside workspace"):
        _parse_game_entries("C:/Windows/win.ini", is_file=True)


def test_offline_etl_llm_status_is_degraded():
    """P1: use_llm=false is offline ETL, not a failed game analysis."""
    from lichess_analyzer_mcp.services.compact_serializer import _llm

    out = _llm({"status": "degraded", "provider": "deterministic", "reason": "llm_disabled"})
    assert out["status"] == "degraded"
    failed = _llm(
        {"status": "degraded", "provider": "deterministic", "reason": "all_providers_failed"}
    )
    assert failed["status"] == "failed"


def test_get_engine_default_reuses_configured_hash(monkeypatch):
    """P1: a bare get_engine() reconfigured 128 MB to 512 MB."""
    from lichess_analyzer_mcp.services import engine_client as ec

    class FakeEngine:
        def __init__(self):
            self.calls = []

        def configure(self, cfg):
            self.calls.append(cfg)

    fake = FakeEngine()
    monkeypatch.setattr(ec, "_engine", fake)
    monkeypatch.setattr(ec, "_engine_hash_mb", 128)
    monkeypatch.setattr(ec, "_engine_threads", 1)
    assert ec.get_engine() is fake
    assert fake.calls == []


def test_unknown_engine_binary_is_not_trusted():
    """P1: wanted_hash is None used to mean 'trusted'."""
    from scripts.verify_engine_identity import _hash_ok

    assert _hash_ok(None, "abc") is False
    assert _hash_ok("abc", "abc") is True
    assert _hash_ok("abc", "def") is False
