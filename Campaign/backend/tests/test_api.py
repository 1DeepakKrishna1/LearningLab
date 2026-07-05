"""API / integration tests covering auth, RBAC, and the campaign lifecycle."""
from __future__ import annotations


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_login_and_me(client, admin_headers):
    me = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "admin@local"
    assert "admin" in [r["name"] for r in me.json()["roles"]]


def test_login_bad_password(client):
    resp = client.post("/api/v1/auth/login", data={"username": "admin@local", "password": "nope"})
    assert resp.status_code == 401


def test_refresh_flow(client):
    login = client.post("/api/v1/auth/login", data={"username": "admin@local", "password": "Admin@123"})
    refresh = login.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    # Old refresh token is now revoked (rotation).
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_viewer_cannot_create_campaign(client, viewer_headers):
    payload = {"name": "X", "type": "one_time", "channel": "email"}
    resp = client.post("/api/v1/campaigns", json=payload, headers=viewer_headers)
    assert resp.status_code == 403


def test_template_crud_and_preview(client, marketer_headers):
    create = client.post("/api/v1/templates", headers=marketer_headers, json={
        "name": "Test Email", "channel": "email", "subject": "Hi {{first_name}}",
        "html_content": "<p>Hello {{first_name}}</p>", "variables": ["first_name"],
    })
    assert create.status_code == 201, create.text
    tid = create.json()["id"]
    preview = client.post(f"/api/v1/templates/{tid}/preview", headers=marketer_headers,
                          json={"sample": {"first_name": "Sam"}})
    assert preview.status_code == 200
    assert "Sam" in preview.json()["body"]


def test_segment_preview_matches_seed(client, marketer_headers):
    resp = client.post("/api/v1/segments/preview", headers=marketer_headers, json={
        "name": "tmp", "definition": {"op": "AND", "rules": [
            {"field": "tags", "operator": "contains", "value": "vip"}]},
    })
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_full_campaign_lifecycle(client, marketer_headers):
    # Need a template + segment.
    tpl = client.post("/api/v1/templates", headers=marketer_headers, json={
        "name": "LC Email", "channel": "email", "subject": "Hi", "html_content": "<p>Hi {{first_name}}</p>",
    }).json()
    seg = client.post("/api/v1/segments", headers=marketer_headers, json={
        "name": "LC Seg", "definition": {"op": "AND", "rules": [
            {"field": "country", "operator": "eq", "value": "US"}]},
    }).json()

    camp = client.post("/api/v1/campaigns", headers=marketer_headers, json={
        "name": "Lifecycle Test", "type": "one_time", "channel": "email",
        "template_id": tpl["id"], "segment_id": seg["id"],
    })
    assert camp.status_code == 201, camp.text
    cid = camp.json()["id"]
    assert camp.json()["status"] == "draft"

    assert client.post(f"/api/v1/campaigns/{cid}/submit", headers=marketer_headers).json()["status"] == "pending_approval"
    approved = client.post(f"/api/v1/campaigns/{cid}/approve", headers=marketer_headers, json={"approved": True})
    assert approved.json()["status"] == "approved"

    # Immediate send.
    sent = client.post(f"/api/v1/campaigns/{cid}/schedule", headers=marketer_headers, json={"scheduled_at": None})
    assert sent.status_code == 200

    # Deliveries should eventually exist (background task runs in TestClient lifespan).
    deliveries = client.get(f"/api/v1/campaigns/{cid}/deliveries", headers=marketer_headers)
    assert deliveries.status_code == 200


def test_illegal_transition_rejected(client, marketer_headers):
    camp = client.post("/api/v1/campaigns", headers=marketer_headers, json={
        "name": "Bad Transition", "type": "one_time", "channel": "sms",
    }).json()
    # Cannot approve a draft (must submit first).
    resp = client.post(f"/api/v1/campaigns/{camp['id']}/approve", headers=marketer_headers, json={"approved": True})
    assert resp.status_code == 409


def test_csv_import(client, marketer_headers):
    csv_content = "email,first_name,country,tags\nnew1@example.com,New,US,beta;promo\n"
    resp = client.post("/api/v1/contacts/import", headers=marketer_headers,
                       files={"file": ("contacts.csv", csv_content, "text/csv")})
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] >= 1
