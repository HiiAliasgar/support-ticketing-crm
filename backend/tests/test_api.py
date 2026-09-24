import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main as app_module
from app.database import Base, get_db
from app.seed import maybe_seed_users

TICKET_PAYLOAD = {
    "customer_name": "Ada Lovelace",
    "customer_email": "ada@analytic.example",
    "subject": "Cannot export monthly report",
    "description": "Export button returns a 502 for last month's report.",
}


@pytest.fixture()
def client(tmp_path) -> TestClient:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    maybe_seed_users(TestingSessionLocal())

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[get_db] = override_get_db
    with TestClient(app_module.app) as test_client:
        yield test_client
    app_module.app.dependency_overrides.clear()


def test_create_ticket_returns_generated_id(client):
    response = client.post("/api/tickets", json=TICKET_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["ticket_id"] == "TKT-0001"
    assert body["created_at"]

    second = client.post("/api/tickets", json={**TICKET_PAYLOAD, "customer_name": "Grace Hopper"})
    assert second.status_code == 201
    assert second.json()["ticket_id"] == "TKT-0002"


def test_create_ticket_validates_payload(client):
    bad_email = client.post("/api/tickets", json={**TICKET_PAYLOAD, "customer_email": "not-an-email"})
    assert bad_email.status_code == 422

    missing_field = client.post("/api/tickets", json={k: v for k, v in TICKET_PAYLOAD.items() if k != "subject"})
    assert missing_field.status_code == 422


def test_list_tickets_and_filters(client):
    client.post("/api/tickets", json=TICKET_PAYLOAD)
    client.post(
        "/api/tickets",
        json={
            **TICKET_PAYLOAD,
            "customer_name": "Alan Turing",
            "customer_email": "alan@example.com",
            "subject": "Billing question",
        },
    )

    all_tickets = client.get("/api/tickets")
    assert all_tickets.status_code == 200
    assert len(all_tickets.json()) == 2

    open_tickets = client.get("/api/tickets", params={"status": "Open"})
    assert len(open_tickets.json()) == 2
    assert client.get("/api/tickets", params={"status": "Closed"}).json() == []

    by_name = client.get("/api/tickets", params={"search": "Ada"})
    assert len(by_name.json()) == 1
    by_subject = client.get("/api/tickets", params={"search": "Billing"})
    assert len(by_subject.json()) == 1
    by_email = client.get("/api/tickets", params={"search": "alan@example"})
    assert len(by_email.json()) == 1

    invalid_status = client.get("/api/tickets", params={"status": "Bogus"})
    assert invalid_status.status_code == 422


def test_get_ticket_detail(client):
    created = client.post("/api/tickets", json=TICKET_PAYLOAD).json()
    detail = client.get(f"/api/tickets/{created['ticket_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["customer_email"] == "ada@analytic.example"
    assert body["description"].startswith("Export button")
    assert body["notes"] == []

    missing = client.get("/api/tickets/TKT-9999")
    assert missing.status_code == 404


def test_update_status_and_add_note(client):
    created = client.post("/api/tickets", json=TICKET_PAYLOAD).json()
    ticket_id = created["ticket_id"]

    updated = client.put(
        f"/api/tickets/{ticket_id}",
        json={"status": "In Progress", "note_text": "Investigating the export worker."},
    )
    assert updated.status_code == 200
    assert updated.json()["success"] is True

    detail = client.get(f"/api/tickets/{ticket_id}").json()
    assert detail["status"] == "In Progress"
    assert detail["notes"][0]["note_text"] == "Investigating the export worker."

    note_only = client.put(f"/api/tickets/{ticket_id}", json={"note_text": "Found root cause."})
    assert note_only.status_code == 200
    assert len(client.get(f"/api/tickets/{ticket_id}").json()["notes"]) == 2

    invalid = client.put(f"/api/tickets/{ticket_id}", json={"status": "Nope"})
    assert invalid.status_code == 422


def test_dedicated_notes_endpoint(client):
    created = client.post("/api/tickets", json=TICKET_PAYLOAD).json()
    note = client.post(
        f"/api/tickets/{created['ticket_id']}/notes",
        json={"note_text": "Customer replied with logs.", "author": "Riley"},
    )
    assert note.status_code == 201
    assert note.json()["author"] == "Riley"

    missing = client.post("/api/tickets/TKT-9999/notes", json={"note_text": "hi"})
    assert missing.status_code == 404


def test_dashboard_counts(client):
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["total"] == 0

    client.post("/api/tickets", json=TICKET_PAYLOAD)
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["total"] == 1
    assert dashboard["open_count"] == 1


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# --- Auth -----------------------------------------------------------------
def auth_headers(client, username="aliasgar", password="SupportTick2026!"):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_me(client):
    response = client.post(
        "/api/auth/login", json={"username": "aliasgar", "password": "SupportTick2026!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user"]["role"] == "admin"
    assert body["user"]["username"] == "aliasgar"

    me = client.get("/api/auth/me", headers=auth_headers(client))
    assert me.status_code == 200
    assert me.json()["username"] == "aliasgar"

    bad = client.post("/api/auth/login", json={"username": "aliasgar", "password": "wrong"})
    assert bad.status_code == 401

    missing_token = client.get("/api/auth/me")
    assert missing_token.status_code == 401

    agent_login = client.post("/api/auth/login", json={"username": "riley", "password": "agent123456"})
    assert agent_login.status_code == 200
    assert agent_login.json()["user"]["role"] == "agent"


def test_logout_invalidates_session(client):
    headers = auth_headers(client)
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).json()["success"] is True
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_admin_routes_require_admin(client):
    agent_headers = auth_headers(client, "riley", "agent123456")
    admin_headers = auth_headers(client)

    anon = client.get("/api/admin/agents")
    assert anon.status_code == 401

    agent = client.get("/api/admin/agents", headers=agent_headers)
    assert agent.status_code == 403

    admin = client.get("/api/admin/agents", headers=admin_headers)
    assert admin.status_code == 200
    usernames = {u["username"] for u in admin.json()}
    assert {"aliasgar", "riley", "hannah", "devon"} <= usernames


def test_admin_crud_agents(client):
    headers = auth_headers(client)
    created = client.post(
        "/api/admin/agents",
        headers=headers,
        json={"username": "taylor", "display_name": "Taylor Reid", "password": "taylors123"},
    )
    assert created.status_code == 201
    agent_id = created.json()["id"]

    duplicate = client.post(
        "/api/admin/agents",
        headers=headers,
        json={"username": "taylor", "display_name": "X", "password": "something123"},
    )
    assert duplicate.status_code == 409

    patched = client.patch(
        f"/api/admin/agents/{agent_id}",
        headers=headers,
        json={"active": False, "display_name": "Taylor R."},
    )
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert patched.json()["display_name"] == "Taylor R."

    admin_id = next(u["id"] for u in client.get("/api/admin/agents", headers=headers).json() if u["username"] == "aliasgar")

    demote_self = client.patch(f"/api/admin/agents/{admin_id}", headers=headers, json={"role": "agent"})
    assert demote_self.status_code == 422

    deactivate_self = client.patch(f"/api/admin/agents/{admin_id}", headers=headers, json={"active": False})
    assert deactivate_self.status_code == 422


def test_admin_settings(client):
    headers = auth_headers(client)
    updated = client.put(
        "/api/admin/settings",
        headers=headers,
        json={"workspace_name": "Acme Support", "ticket_prefix": "SUP", "sla_hours": 8},
    )
    assert updated.status_code == 200
    assert updated.json()["workspace_name"] == "Acme Support"
    assert updated.json()["ticket_prefix"] == "SUP"

    created = client.post("/api/tickets", json=TICKET_PAYLOAD)
    assert created.json()["ticket_id"].startswith("SUP-")


def test_admin_audit_and_export(client):
    headers = auth_headers(client)
    client.put("/api/admin/settings", headers=headers, json={"sla_hours": 12})
    ticket = client.post("/api/tickets", json=TICKET_PAYLOAD).json()

    audit = client.get("/api/admin/audit", headers=headers)
    assert audit.status_code == 200
    actions = [e["action"] for e in audit.json()["items"]]
    assert "settings.update" in actions

    exported = client.get("/api/admin/export", headers=headers)
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert exported.headers["content-disposition"].startswith("attachment")
    assert "ticket_id" in exported.text


def test_bulk_status_and_delete_ticket(client):
    headers = auth_headers(client)
    first = client.post("/api/tickets", json=TICKET_PAYLOAD).json()
    second = client.post(
        "/api/tickets", json={**TICKET_PAYLOAD, "customer_name": "Grace Hopper"}
    ).json()
    ids = [first["ticket_id"], second["ticket_id"]]

    bulk = client.post(
        "/api/admin/tickets/bulk-status",
        headers=headers,
        json={"status": "Closed", "ticket_ids": ids},
    )
    assert bulk.status_code == 200
    assert bulk.json()["updated"] == 2
    for tid in ids:
        detail = client.get(f"/api/tickets/{tid}").json()
        assert detail["status"] == "Closed"

    agent_headers = auth_headers(client, "riley", "agent123456")
    as_agent = client.delete(f"/api/tickets/{ids[0]}", headers=agent_headers)
    assert as_agent.status_code == 403

    deleted = client.delete(f"/api/tickets/{ids[0]}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/tickets/{ids[0]}").status_code == 404


# --- Priority / assignee / pagination --------------------------------------
def test_create_with_priority_and_filter(client):
    created = client.post(
        "/api/tickets", json={**TICKET_PAYLOAD, "priority": "Urgent"}
    )
    assert created.status_code == 201
    detail = client.get(f"/api/tickets/{created.json()['ticket_id']}").json()
    assert detail["priority"] == "Urgent"

    low = client.post("/api/tickets", json={**TICKET_PAYLOAD, "priority": "Low", "customer_name": "Barbara"})
    urgent = client.get("/api/tickets", params={"priority": "Urgent"}).json()
    assert len(urgent) == 1
    assert urgent[0]["priority"] == "Urgent"

    invalid = client.post("/api/tickets", json={**TICKET_PAYLOAD, "priority": "Nope"})
    assert invalid.status_code == 422

    filtered = client.get("/api/tickets", params={"status": "Open", "priority": "Urgent"})
    assert filtered.status_code == 200


def test_assign_ticket(client):
    headers = auth_headers(client)
    agents = {a["username"]: a for a in client.get("/api/agents").json()}
    riley = agents["riley"]

    created = client.post("/api/tickets", json=TICKET_PAYLOAD).json()
    tid = created["ticket_id"]

    assigned = client.post(
        f"/api/tickets/{tid}/assign", headers=headers, json={"assignee_id": riley["id"]}
    )
    assert assigned.status_code == 200
    detail = client.get(f"/api/tickets/{tid}").json()
    assert detail["assignee_id"] == riley["id"]
    assert detail["assignee_name"] == "Riley Patel"

    unassigned = client.post(f"/api/tickets/{tid}/assign", headers=headers, json={"assignee_id": None})
    assert unassigned.status_code == 200
    assert client.get(f"/api/tickets/{tid}").json()["assignee_id"] is None

    bad = client.post(f"/api/tickets/{tid}/assign", headers=headers, json={"assignee_id": 99999})
    assert bad.status_code == 422


def test_ticket_pagination(client):
    for name in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        client.post("/api/tickets", json={**TICKET_PAYLOAD, "customer_name": name})

    page1 = client.get("/api/tickets", params={"page": 1, "per_page": 4}).json()
    assert page1["total"] == 10
    assert len(page1["items"]) == 4
    assert page1["pages"] == 3

    page3 = client.get("/api/tickets", params={"page": 3, "per_page": 4}).json()
    assert len(page3["items"]) == 2

    default_list = client.get("/api/tickets").json()
    assert isinstance(default_list, list)
    assert len(default_list) == 10