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


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except (ValueError, TypeError):
            return err.code, raw.decode("utf-8", "replace")


def wait_ready(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, _ = request("GET", "/health")
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

        status, created = request(
            "POST",
            "/api/tickets",
            {"customer_name": "Alice Example", "customer_email": "alice@example.com",
             "subject": "Smoke test", "description": "E2E verification."},
        )
        assert status == 201 and created["ticket_id"], created
        assert created["ticket_id"].startswith("TKT-")
        print("[2] created", created)

        status, items = request("GET", "/api/tickets")
        assert status == 200 and len(items) > 1  # 15 seeded + 1 new
        assert all(t["ticket_id"].startswith("TKT-") for t in items)

        status, hits = request("GET", "/api/tickets?search=smoke")
        assert status == 200 and len(hits) == 1

        status, hits = request("GET", "/api/tickets?status=Open")
        assert status == 200 and len(hits) >= 1
        status, hits = request("GET", "/api/tickets?status=Bogus")
        assert status == 422
        print("[3] list/search/filter OK")

        status, detail = request("GET", f"/api/tickets/{created['ticket_id']}")
        assert status == 200 and detail["description"].startswith("E2E")
        assert detail["notes"] == []

        status, updated = request(
            "PUT",
            f"/api/tickets/{created['ticket_id']}",
            {"status": "In Progress", "note_text": "Investigating."},
        )
        assert status == 200 and updated["success"] is True

        status, detail = request("GET", f"/api/tickets/{created['ticket_id']}")
        assert detail["status"] == "In Progress" and len(detail["notes"]) == 1

        status, note = request(
            "POST",
            f"/api/tickets/{created['ticket_id']}/notes",
            {"note_text": "Root cause found.", "author": "Riley"},
        )
        assert status == 201 and note["author"] == "Riley"
        print("[4] detail/update/notes OK")

        status, dash = request("GET", "/api/dashboard")
        assert status == 200 and dash["total"] == 16  # 15 seeded + 1 created
        assert dash["open_count"] >= 1 and dash["in_progress_count"] >= 1
        print("[5] dashboard OK")

        # Frontend + SPA routing
        for path in ("/", f"/tickets/{created['ticket_id']}", "/new"):
            req = urllib.request.Request(BASE + path)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode()
                assert 'id="root"' in html and resp.status == 200, path
        print("[6] frontend + SPA fallback OK")

        # static asset served (find a real asset path from the built index.html)
        with urllib.request.urlopen(BASE + "/", timeout=15) as resp:
            index_html = resp.read().decode()
        import re

        asset_path = re.search(r'(/assets/[^"\']+)', index_html)
        assert asset_path, "no asset reference found in index.html"
        with urllib.request.urlopen(BASE + asset_path.group(1), timeout=15) as resp:
            assert resp.status == 200 and int(resp.headers.get("content-length", "1")) > 0
        print("[7] static assets OK")

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