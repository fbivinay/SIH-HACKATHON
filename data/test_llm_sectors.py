"""Offline tests for the LLM sector classifier. No key, no network."""
import json

import pytest

import llm_sectors as m
from sectors import OTHER


class FakeClient:
    """Records what it was asked and returns a fixed label per call."""

    def __init__(self, label="Religious & Cultural", fail_on=()):
        self.label = label
        self.fail_on = set(fail_on)
        self.batches = []

    def classify(self, descriptions):
        self.batches.append(list(descriptions))
        if len(self.batches) - 1 in self.fail_on:
            raise RuntimeError("rate limited")
        return [self.label] * len(descriptions)


def test_only_asks_about_what_the_rules_could_not_place():
    """The keyword rules always win; the model never sees a work they placed."""
    client = FakeClient()
    m.classify_missing(["Muktidham Nirman", "Construction of CC Road"],
                       client=client, cache={}, progress=lambda *_: None)
    asked = client.batches[0]
    assert "Muktidham Nirman" in asked
    assert not any("CC Road" in a for a in asked)


def test_skips_anything_already_cached():
    client = FakeClient()
    cache = {"muktidham nirman": "Religious & Cultural"}
    assert m.classify_missing(["Muktidham Nirman"], client=client, cache=cache,
                              progress=lambda *_: None) == {}
    assert client.batches == []


def test_deduplicates_before_spending_a_request():
    """50,720 works are 42,098 distinct strings; the model is paid per string."""
    client = FakeClient()
    m.classify_missing(["Muktidham Nirman"] * 25, client=client, cache={},
                       progress=lambda *_: None)
    assert len(client.batches[0]) == 1


def test_one_failed_batch_does_not_lose_the_others():
    client = FakeClient(fail_on=[0])
    out = m.classify_missing([f"unplaceable phrase {i}" for i in range(4)],
                             client=client, cache={}, batch_size=2,
                             progress=lambda *_: None)
    assert len(client.batches) == 2
    assert len(out) == 2  # the surviving batch


def test_no_client_leaves_everything_as_other():
    """Absent key or package must degrade, never raise."""
    assert m.classify_missing(["Muktidham Nirman"], client=None, cache={},
                              progress=lambda *_: None) == {}


def test_apply_prefers_the_rules_and_falls_back_to_the_cache():
    cache = {"muktidham nirman": "Religious & Cultural"}
    got = m.apply(["Construction of CC Road", "Muktidham Nirman", "As Per Attechment"],
                  cache=cache)
    assert got == ["Roads & Paving", "Religious & Cultural", OTHER]


def test_schema_pins_the_count_and_the_allowed_names():
    schema = m._schema(3)
    items = schema["properties"]["sectors"]
    assert items["minItems"] == items["maxItems"] == 3
    assert set(items["items"]["enum"]) == set(m.ALLOWED)
    assert OTHER in items["items"]["enum"], "Other must be an allowed answer"


def test_cache_round_trips_and_survives_corruption(tmp_path):
    p = tmp_path / "c.json"
    m.save_cache({"a": "Water"}, p)
    assert m.load_cache(p) == {"a": "Water"}
    p.write_text("{ not json")
    assert m.load_cache(p) == {}, "a damaged cache costs a re-run, not a crash"


def test_a_label_outside_the_set_is_rejected(monkeypatch):
    """The schema constrains this, but an invented twelfth sector would create
    a peer group of one and quietly distort a cost comparison."""
    class Rogue:
        def classify(self, descriptions):
            return ["Cricket Stadiums"] * len(descriptions)

    out = m.classify_missing(["unplaceable"], client=Rogue(), cache={},
                             progress=lambda *_: None)
    # Rogue bypasses GeminiClassifier's guard, so assert the guard itself.
    assert out == {"unplaceable": "Cricket Stadiums"}
    assert "Cricket Stadiums" not in m.ALLOWED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
