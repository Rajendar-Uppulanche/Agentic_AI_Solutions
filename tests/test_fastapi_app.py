from fastapi.testclient import TestClient

from app_fastapi import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_triage_requires_alert():
    resp = client.post("/triage", json={})
    assert resp.status_code == 422


def test_triage_langgraph_requires_alert():
    resp = client.post("/triage-langgraph", json={})
    assert resp.status_code == 422


def test_triage_gemini_requires_alert():
    resp = client.post("/triage-gemini", json={})
    assert resp.status_code == 422


def test_triage_vertex_requires_alert():
    resp = client.post("/triage-vertex", json={})
    assert resp.status_code == 422
