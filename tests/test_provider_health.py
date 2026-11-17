"""P1-6: permanent provider states get a realistic negative-cache TTL."""

from lichess_analyzer_mcp.services import provider_health


def test_permanent_and_payment_statuses_are_not_retried_every_minute():
    provider_health.reset()
    try:
        provider_health.record_result("nvidia", 410, "Gone")
        provider_health.record_result("cerebras", 402, "Insufficient credits")
        provider_health.record_result("deepseek", 500, "Server error")
        snap = provider_health.snapshot()
        assert snap["nvidia"]["retry_in_s"] >= 86000  # 24 h, not 35-58 s
        assert snap["cerebras"]["retry_in_s"] >= 3500  # 1 h
        assert snap["deepseek"]["retry_in_s"] <= 60  # transient stays short
    finally:
        provider_health.reset()
