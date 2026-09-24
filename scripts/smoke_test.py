"""End-to-end smoke test against a real uvicorn server.

Launches the FastAPI app (serving the built React frontend), exercises every
API endpoint plus SPA routing, then shuts the server down.

Usage:  python scripts/smoke_test.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"


def request(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers=req_headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            payload = raw
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype:
                payload = json.loads(raw) if raw else None
            else:
                payload = raw.decode("utf-8", "replace")
            return resp.status, payload, resp.headers
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw), err.headers
        except (ValueError, TypeError):
            return err.code, raw.decode("utf-8", "replace"), err.headers


def wait_ready(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _, _ = request("GET", "/health")
            if status == 200:
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def main():
    tmp = tempfile.mkdtemp(prefix="supporttick-smoke-")
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{tmp.replace(os.sep, '/')}/smoke.db"
    env["AUTO_SEED_DEMO"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        if not wait_ready():
            raise SystemExit("Server did not become ready")
        print("[1] server ready")

        status, created, _ = request(
            "POST",
            "/api/tickets",
            {"customer_name": "Alice Example", "customer_email": "alice@example.com",
             "subject": "Smoke test", "description": "E2E verification."},
        )
        assert status == 201 and created["ticket_id"], created
        assert created["ticket_id"].startswith("TKT-")
        print("[2] created", created)

        status, items, _ = request("GET", "/api/tickets")
        assert status == 200 and len(items) > 1  # 15 seeded + 1 new
        assert all(t["ticket_id"].startswith("TKT-") for t in items)

        status, hits, _ = request("GET", "/api/tickets?search=smoke")
        assert status == 200 and len(hits) == 1

        status, hits, _ = request("GET", "/api/tickets?status=Open")
        assert status == 200 and len(hits) >= 1
        status, hits, _ = request("GET", "/api/tickets?status=Bogus")
        assert status == 422
        print("[3] list/search/filter OK")

        status, detail, _ = request("GET", f"/api/tickets/{created['ticket_id']}")
        assert status == 200 and detail["description"].startswith("E2E")
        assert detail["notes"] == []

        status, updated, _ = request(
            "PUT",
            f"/api/tickets/{created['ticket_id']}",
            {"status": "In Progress", "note_text": "Investigating."},
        )
        assert status == 200 and updated["success"] is True

        status, detail, _ = request("GET", f"/api/tickets/{created['ticket_id']}")
        assert detail["status"] == "In Progress" and len(detail["notes"]) == 1

        status, note, _ = request(
            "POST",
            f"/api/tickets/{created['ticket_id']}/notes",
            {"note_text": "Root cause found.", "author": "Riley"},
        )
        assert status == 201 and note["author"] == "Riley"
        print("[4] detail/update/notes OK")

        status, dash, _ = request("GET", "/api/dashboard")
        assert status == 200 and dash["total"] == 16  # 15 seeded + 1 created
        assert dash["open_count"] >= 1 and dash["in_progress_count"] >= 1
        assert isinstance(dash["by_priority"], dict) and sum(dash["by_priority"].values()) == 16
        print("[5] dashboard OK")

        # --- Auth ----------------------------------------------------------
        status, login_body, _ = request(
            "POST", "/api/auth/login", {"username": "aliasgar", "password": "SupportTick2026!"}
        )
        assert status == 200, login_body
        token = login_body["token"]
        assert login_body["user"]["role"] == "admin"
        auth = {"Authorization": f"Bearer {token}"}

        status, me, _ = request("GET", "/api/auth/me", headers=auth)
        assert status == 200 and me["username"] == "aliasgar"

        status, bad, _ = request(
            "POST", "/api/auth/login", {"username": "aliasgar", "password": "nope"}
        )
        assert status == 401
        print("[6] login/me OK")

        # --- Admin ---------------------------------------------------------
        status, anon, _ = request("GET", "/api/admin/agents")
        assert status == 401

        status, agents, _ = request("GET", "/api/admin/agents", headers=auth)
        assert status == 200 and len(agents) >= 4
        riley = next(a for a in agents if a["username"] == "riley")

        status, patched, _ = request(
            "PATCH", f"/api/admin/agents/{riley['id']}", {"display_name": "Riley P."}, auth
        )
        assert status == 200 and patched["display_name"] == "Riley P."

        status, created_agent, _ = request(
            "POST",
            "/api/admin/agents",
            {"username": "nova", "display_name": "Nova Chen", "password": "nova123456"},
            auth,
        )
        assert status == 201 and created_agent["username"] == "nova"

        status, duplicate, _ = request(
            "POST",
            "/api/admin/agents",
            {"username": "nova", "display_name": "X", "password": "nova123456"},
            auth,
        )
        assert status == 409

        status, settings, _ = request("GET", "/api/admin/settings", headers=auth)
        assert status == 200 and settings["ticket_prefix"] == "TKT"

        status, saved, _ = request(
            "PUT",
            "/api/admin/settings",
            {"workspace_name": "Acme Support", "ticket_prefix": "SUP", "sla_hours": 8},
            auth,
        )
        assert status == 200 and saved["ticket_prefix"] == "SUP"
        print("[7] admin agents/settings OK")

        # --- Priority / assign / filter / pagination ------------------------
        status, prio, _ = request(
            "POST",
            "/api/tickets",
            {"customer_name": "Bob Urgent", "customer_email": "bob@example.com",
             "subject": "Blocker", "description": "Priority test", "priority": "Urgent"},
        )
        assert status == 201 and prio["priority"] if "priority" in prio else True
        assert prio["ticket_id"].startswith("SUP-")
        status, prio_detail, _ = request("GET", f"/api/tickets/{prio['ticket_id']}")
        assert prio_detail["priority"] == "Urgent"
        print("[8] priority+prefix OK")

        status, assigned, _ = request(
            "POST", f"/api/tickets/{prio['ticket_id']}/assign", {"assignee_id": riley["id"]}, auth
        )
        assert status == 200 and assigned["assignee_name"]
        status, detail, _ = request("GET", f"/api/tickets/{prio['ticket_id']}")
        assert detail["assignee_id"] == riley["id"]

        status, filtered, _ = request("GET", "/api/tickets?priority=Urgent&status=Open")
        assert status == 200
        assert all(t["priority"] == "Urgent" for t in filtered)
        assert any(t["ticket_id"] == prio["ticket_id"] for t in filtered)

        status, all_urgent, _ = request("GET", "/api/tickets?priority=Urgent")
        assert status == 200 and all(t["priority"] == "Urgent" for t in all_urgent)

        status, page1, _ = request("GET", "/api/tickets?priority=Urgent&page=1&per_page=1")
        assert status == 200 and len(page1["items"]) == 1 and page1["total"] == len(all_urgent)
        print("[9] assign/filter/pagination OK")

        # --- Audit / export / logout -----------------------------------------
        status, audit, _ = request("GET", "/api/admin/audit?per_page=50", headers=auth)
        assert status == 200 and audit["total"] >= 3
        actions = {e["action"] for e in audit["items"]}
        assert "settings.update" in actions

        status, csv_text, csv_headers = request("GET", "/api/admin/export", headers=auth)
        assert status == 200
        assert "text/csv" in csv_headers.get("content-type", "")
        lines = csv_text.strip().splitlines()
        assert lines and "ticket_id" in lines[0]

        status, out, _ = request("POST", "/api/auth/logout", headers=auth)
        assert status == 200 and out["success"] is True
        status, me_after, _ = request("GET", "/api/auth/me", headers=auth)
        assert status == 401
        print("[10] audit/export/logout OK")

        # --- Frontend + SPA routing ------------------------------------------
        for path in ("/", f"/tickets/{created['ticket_id']}", "/new", "/login"):
            req = urllib.request.Request(BASE + path)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode()
                assert 'id="root"' in html and resp.status == 200, path
        print("[11] frontend + SPA fallback OK")

        # static asset served (find a real asset path from the built index.html)
        with urllib.request.urlopen(BASE + "/", timeout=15) as resp:
            index_html = resp.read().decode()
        import re

        asset_path = re.search(r'(/assets/[^"\']+)', index_html)
        assert asset_path, "no asset reference found in index.html"
        with urllib.request.urlopen(BASE + asset_path.group(1), timeout=15) as resp:
            assert resp.status == 200 and int(resp.headers.get("content-length", "1")) > 0
        print("[12] static assets OK")

        print("\nSMOKE TEST PASSED")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

        err = proc.stderr.read().decode()
        if err:
            print("--- server stderr ---")
            print(err[-1500:])


if __name__ == "__main__":
    main()