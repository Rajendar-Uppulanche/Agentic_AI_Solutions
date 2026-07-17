import pytest

from app_flask import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_triage_requires_alert(client):
    resp = client.post("/triage", json={})
    assert resp.status_code == 400


def test_triage_langgraph_requires_alert(client):
    resp = client.post("/triage-langgraph", json={})
    assert resp.status_code == 400


def test_triage_gemini_requires_alert(client):
    resp = client.post("/triage-gemini", json={})
    assert resp.status_code == 400


def test_triage_vertex_requires_alert(client):
    resp = client.post("/triage-vertex", json={})
    assert resp.status_code == 400
