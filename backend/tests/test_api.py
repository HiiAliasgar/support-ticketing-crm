import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main as app_module
from app.database import Base, get_db

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