# -*- coding: utf-8 -*-
import types

from app.core.utils import rate_limit_policy


def _fake_app(config):
    return types.SimpleNamespace(config=config)


def test_expand_limit_value_supports_per_and_slash_formats():
    assert rate_limit_policy.expand_limit_value("1 per minute;5 per hour", 100) == "100 per minute;500 per hour"
    assert rate_limit_policy.expand_limit_value("10/minute;60/hour", 100) == "1000/minute;6000/hour"


def test_production_policy_expands_decorator_and_manual_limits(monkeypatch):
    monkeypatch.setattr(rate_limit_policy, "_CONFIGURED_EXPAND_LIMITS", None)
    monkeypatch.setattr(rate_limit_policy, "_CONFIGURED_MULTIPLIER", None)

    rate_limit_policy.configure_rate_limit_policy(_fake_app({
        "DEBUG": False,
        "TESTING": False,
        "RATELIMIT_LIMIT_MULTIPLIER": 100,
    }))

    assert rate_limit_policy.expand_rate_limit("3/minute;10 per hour") == "300/minute;1000 per hour"
    assert rate_limit_policy.expand_manual_rate_limit_count(5) == 500
    assert rate_limit_policy.relax_manual_rate_limit_interval(60) == 1


def test_debug_policy_keeps_original_limits(monkeypatch):
    monkeypatch.setattr(rate_limit_policy, "_CONFIGURED_EXPAND_LIMITS", None)
    monkeypatch.setattr(rate_limit_policy, "_CONFIGURED_MULTIPLIER", None)

    rate_limit_policy.configure_rate_limit_policy(_fake_app({
        "DEBUG": True,
        "TESTING": False,
        "RATELIMIT_LIMIT_MULTIPLIER": 100,
    }))

    assert rate_limit_policy.expand_rate_limit("3/minute;10 per hour") == "3/minute;10 per hour"
    assert rate_limit_policy.expand_manual_rate_limit_count(5) == 5
    assert rate_limit_policy.relax_manual_rate_limit_interval(60) == 60
