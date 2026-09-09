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
