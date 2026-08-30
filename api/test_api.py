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
