"""Auto strategy resolves from transformers availability."""

from __future__ import annotations

import builtins

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def test_auto_falls_back_to_rules_when_transformers_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers":
            raise ModuleNotFoundError("No module named 'transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    reset_auto_strategy()
    v, s = classify("anything", None, strategy="auto")
    assert v == "unclear"
    assert s == 0.0


def test_auto_falls_back_to_rules_when_torch_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "torch":
            raise ModuleNotFoundError("No module named 'torch'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    reset_auto_strategy()
    v, s = classify("anything", None, strategy="auto")
    assert v == "unclear"
    assert s == 0.0
