"""Integration tests over the HTTP API (FastAPI TestClient)."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["tools"] > 0


def test_requires_auth(client):
    assert client.get("/api/tools").status_code == 401
    assert client.get("/api/workflows").status_code == 401


def test_login_and_list_tools(client, auth_headers):
    r = client.get("/api/tools", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) > 100


def test_node_catalog(client, auth_headers):
    r = client.get("/api/tools/catalog/nodes", headers=auth_headers)
    data = r.json()
    assert set(data["static"]) == {"trigger", "agent", "logic", "action"}
    assert data["tools"]  # tool nodes grouped by category


def test_tool_get_by_id(client, auth_headers):
    r = client.get("/api/tools/outlook.send_email", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["class_name"] == "SendEmailTool"


def test_create_and_run_workflow(client, auth_headers):
    create = client.post("/api/workflows", headers=auth_headers, json={
        "name": "API WF",
        "nodes": [
            {"id": "n1", "type": "trigger.manual", "data": {"config": {}}},
            {"id": "n2", "type": "action.generate_report",
             "data": {"config": {"title": "Hi", "format": "json"}}},
        ],
        "edges": [{"source": "n1", "target": "n2"}],
    })
    assert create.status_code == 200
    wf_id = create.json()["id"]

    validate = client.get(f"/api/workflows/{wf_id}/validate", headers=auth_headers)
    assert validate.json()["valid"] is True

    run = client.post(f"/api/workflows/{wf_id}/run", headers=auth_headers, json={})
    assert run.status_code == 200
    assert "execution_id" in run.json()


def test_agent_crud(client, auth_headers):
    created = client.post("/api/agents", headers=auth_headers, json={
        "name": "Reviewer", "role": "reviewer", "tools": ["pdf_tools.pdf_extract_text"]})
    assert created.status_code == 200
    agent_id = created.json()["agent_id"]

    listed = client.get("/api/agent/list", headers=auth_headers)
    assert any(a["agent_id"] == agent_id for a in listed.json())

    deleted = client.delete(f"/api/agents/{agent_id}", headers=auth_headers)
    assert deleted.json()["deleted"] is True


def test_dashboard_and_audit(client, auth_headers):
    assert client.get("/api/monitoring/dashboard", headers=auth_headers).status_code == 200
    assert client.get("/api/audit", headers=auth_headers).status_code == 200


def test_openapi_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/api/workflows" in r.json()["paths"]
