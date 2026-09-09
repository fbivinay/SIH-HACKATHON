from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_overview_returns_totals():
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    assert resp.json()["total_projects"] > 0


def test_projects_list_returns_200_and_list():
    resp = client.get("/api/projects?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_project_detail_404_for_unknown_id():
    resp = client.get("/api/projects/999999999")
    assert resp.status_code == 404


def test_map_states_returns_200():
    resp = client.get("/api/map/states")
    assert resp.status_code == 200


def test_alerts_returns_a_page_with_a_total():
    resp = client.get("/api/alerts?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= len(body["alerts"])
    assert isinstance(body["alerts"], list)


def test_alerts_rejects_an_unknown_review_status():
    assert client.get("/api/alerts?status=approved").status_code == 422


def test_alerts_summary_returns_counts():
    resp = client.get("/api/alerts/summary")
    assert resp.status_code == 200
    body = resp.json()
    # Every reviewed bucket plus the unreviewed one accounts for the whole
    # in-scope set - a work is in exactly one of them.
    assert (
        body["pending"] + body["escalated"] + body["verified"] + body["dismissed"]
        == body["in_scope"]
    )


def test_review_without_the_token_is_rejected(monkeypatch):
    monkeypatch.setenv("REVIEW_TOKEN", "test-token")
    resp = client.post(
        "/api/alerts/review", json={"work_key": "1|18|X", "status": "verified"}
    )
    assert resp.status_code == 401


def test_review_fails_closed_when_no_token_is_configured(monkeypatch):
    """With REVIEW_TOKEN unset nobody can write, rather than everybody."""
    monkeypatch.delenv("REVIEW_TOKEN", raising=False)
    resp = client.post(
        "/api/alerts/review",
        headers={"X-Review-Token": "anything"},
        json={"work_key": "1|18|X", "status": "verified"},
    )
    assert resp.status_code == 503


def test_review_404s_on_a_work_key_that_does_not_exist(monkeypatch):
    monkeypatch.setenv("REVIEW_TOKEN", "test-token")
    resp = client.post(
        "/api/alerts/review",
        headers={"X-Review-Token": "test-token"},
        json={"work_key": "no-such-work|99|NOWHERE", "status": "verified"},
    )
    assert resp.status_code == 404


def test_review_round_trips_and_is_updatable(monkeypatch):
    from db import execute, query

    monkeypatch.setenv("REVIEW_TOKEN", "test-token")
    work = query("SELECT work_key FROM projects WHERE work_key IS NOT NULL LIMIT 1", one=True)
    if work is None:
        return  # nothing loaded; the other tests already cover the shape
    key = work["work_key"]
    try:
        first = client.post(
            "/api/alerts/review",
            headers={"X-Review-Token": "test-token"},
            json={"work_key": key, "status": "escalated", "reviewer": "pytest"},
        )
        assert first.status_code == 200
        assert first.json()["status"] == "escalated"

        # Same work again: the decision is replaced, not duplicated (the table
        # is keyed on work_key, so a second insert would otherwise conflict).
        second = client.post(
            "/api/alerts/review",
            headers={"X-Review-Token": "test-token"},
            json={"work_key": key, "status": "dismissed", "reviewer": "pytest"},
        )
        assert second.status_code == 200
        assert second.json()["status"] == "dismissed"

        listed = client.get("/api/alerts?status=dismissed&limit=200").json()
        assert any(a["work_key"] == key for a in listed["alerts"])
    finally:
        execute("DELETE FROM work_review_events WHERE work_key = %s", [key])
        execute("DELETE FROM work_reviews WHERE work_key = %s", [key])


def test_detector_catalogue_states_a_limit_for_every_detector():
    resp = client.get("/api/detectors")
    assert resp.status_code == 200
    body = resp.json()
    assert {d["code"] for d in body} == {"D-01", "D-02", "D-03", "D-04"}
    for d in body:
        # A finding with no stated limit is what gets a system laughed out of a
        # hearing, so the catalogue must never ship one.
        assert d["limit"].strip()
        assert d["what"].strip()
        assert d["subject"] in ("agency", "mp")


def test_detector_findings_returns_a_page():
    resp = client.get("/api/detectors/findings?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= len(body["findings"])
    for f in body["findings"]:
        assert f["code"].startswith("D-")
        assert 0 < f["severity"] <= 100


def test_detector_findings_filters_by_code():
    body = client.get("/api/detectors/findings?code=D-04&limit=10").json()
    assert all(f["code"] == "D-04" for f in body["findings"])


def test_detector_findings_rejects_an_unknown_subject_type():
    assert client.get("/api/detectors/findings?subject_type=vendor").status_code == 422


def test_detector_findings_come_back_ranked():
    body = client.get("/api/detectors/findings?limit=25").json()
    severities = [f["severity"] for f in body["findings"]]
    assert severities == sorted(severities, reverse=True)


def test_review_history_records_every_decision_not_just_the_last(monkeypatch):
    """Changing a verdict used to overwrite the note explaining the previous
    one. The trail is append-only, so the earlier reason survives."""
    from db import execute, query

    monkeypatch.setenv("REVIEW_TOKEN", "test-token")
    work = query("SELECT work_key FROM projects WHERE work_key IS NOT NULL LIMIT 1", one=True)
    if work is None:
        return
    key = work["work_key"]
    headers = {"X-Review-Token": "test-token"}
    execute("DELETE FROM work_review_events WHERE work_key = %s", [key])
    try:
        client.post("/api/alerts/review", headers=headers, json={
            "work_key": key, "status": "escalated",
            "note": "cost looks off", "reviewer": "pytest"})
        client.post("/api/alerts/review", headers=headers, json={
            "work_key": key, "status": "dismissed", "reviewer": "pytest"})

        resp = client.get("/api/alerts/history", params={"work_key": key})
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 2
        # Newest first, and the escalation's reason is still there.
        assert events[0]["status"] == "dismissed"
        assert events[1]["status"] == "escalated"
        assert events[1]["note"] == "cost looks off"

        # The current verdict is still only the latest one.
        current = query("SELECT status FROM work_reviews WHERE work_key = %s", [key], one=True)
        assert current["status"] == "dismissed"
    finally:
        execute("DELETE FROM work_review_events WHERE work_key = %s", [key])
        execute("DELETE FROM work_reviews WHERE work_key = %s", [key])


def test_review_history_is_empty_for_an_untouched_work():
    resp = client.get("/api/alerts/history", params={"work_key": "no-such-work|99|NOWHERE"})
    assert resp.status_code == 200
    assert resp.json()["events"] == []


def test_overview_anomaly_count_matches_the_queue():
    """The two screens reported different totals for the same set: overview
    counted score > 40 and the queue counts >= 40, a 328-work gap."""
    overview = client.get("/api/overview").json()
    queue = client.get("/api/alerts/summary", params={"min_score": 40}).json()
    assert overview["anomaly_count"] == queue["in_scope"]


def test_agencies_are_bounded_and_exclude_one_work_agencies():
    """An average over one work is whatever that work scored, and those
    agencies were topping the ranking ahead of ones holding a thousand."""
    rows = client.get("/api/agencies?limit=25").json()
    assert len(rows) <= 25
    assert all(r["total_projects"] >= 10 for r in rows)
    scores = [r["avg_risk_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_agencies_paginate():
    first = client.get("/api/agencies?limit=5").json()
    second = client.get("/api/agencies?limit=5&offset=5").json()
    names = {(r["implementing_agency"], r["ls_term"]) for r in first}
    assert not names & {(r["implementing_agency"], r["ls_term"]) for r in second}


def test_states_cover_every_state_with_both_rates():
    rows = client.get("/api/states?ls_term=18").json()
    assert len(rows) >= 30
    for r in rows:
        assert r["state"]
        # Two rates on purpose: the source publishes one number under both
        # names, with utilizationDefinition "vendor_expenditure_legacy".
        for key in ("paid_rate", "committed_rate"):
            assert r[key] is None or 0 <= r[key] <= 200


def test_states_paid_rate_is_expenditure_over_allocation():
    """The figure has to be the weighted one. Averaging the 36 state
    percentages instead gives 33.2% against the correct 34.2%, which is the
    discrepancy between the source's own two pages."""
    rows = client.get("/api/states?ls_term=18").json()
    row = next(r for r in rows if r["allocated"] and r["paid_rate"] is not None)
    expected = float(row["expenditure"]) / float(row["allocated"]) * 100
    assert abs(float(row["paid_rate"]) - expected) < 0.11


def test_compliance_rules_state_their_predicate_and_basis():
    book = client.get("/api/compliance").json()
    assert len(book["rules"]) == 4
    for rule in book["rules"]:
        # A rule you cannot read is a rule you have to take on trust.
        assert rule["predicate"].strip()
        assert rule["basis"].strip()
        assert rule["status"] in ("breached", "clear", "inert")


def test_compliance_separates_a_clear_rule_from_one_that_cannot_fire():
    """Zero breaches means two very different things. C-01 cannot fire at all,
    because the source publishes one figure per completed work that the loader
    records as both sanction and expenditure."""
    rules = {r["code"]: r for r in client.get("/api/compliance").json()["rules"]}
    assert rules["C-01"]["status"] == "inert"
    assert rules["C-01"]["breaches"] == 0
    assert any(r["status"] == "breached" for r in rules.values())


def test_compliance_states_what_it_cannot_check():
    """A rule book listing only what passes is the more misleading half."""
    book = client.get("/api/compliance").json()
    assert len(book["blind_spots"]) >= 3
    for spot in book["blind_spots"]:
        assert spot["name"].strip() and spot["why"].strip()


def test_a_work_can_be_found_by_the_key_that_survives_a_refresh():
    """projects.id is reassigned on every nightly reload, so a link to
    /api/projects/12524 points at a different work tomorrow. work_key does not
    move - that is what makes a shared or bookmarked link durable."""
    from db import query

    work = query(
        "SELECT id, work_key FROM projects WHERE work_key IS NOT NULL LIMIT 1", one=True
    )
    if work is None:
        return
    by_id = client.get(f"/api/projects/{work['id']}").json()
    by_key = client.get("/api/projects/by-key", params={"work_key": work["work_key"]}).json()
    assert by_id["work_key"] == by_key["work_key"] == work["work_key"]
    assert by_id["work_name"] == by_key["work_name"]


def test_by_key_404s_rather_than_guessing():
    assert client.get("/api/projects/by-key",
                      params={"work_key": "no-such|99|WORK"}).status_code == 404
