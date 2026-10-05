"""Deployment and persistence regressions. Tests use disposable local databases."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, insert, select, text
from sqlalchemy.exc import IntegrityError

from test_api import A, device, png, post, reg


@pytest.fixture(autouse=True)
def initialized_database():
    A.initialize_database()


@pytest.mark.parametrize("path", ["/", "/admin", "/shared.css", "/shared.js", "/student.js",
                                 "/admin.js", "/config.js", "/photos.js", "/images/h1-secretary.jpg",
                                 "/images/h2-secretary.jpg"])
def test_pages_and_assets_are_served(path):
    assert device().get(path).status_code == 200


@pytest.mark.parametrize("path", ["/app.py", "/.env", "/hostel.db", "/requirements.txt", "/_files"])
def test_private_files_are_not_served(path):
    assert device().get(path).status_code == 404


def test_health_checks_database():
    response = device().get("/healthz")
    assert response.status_code == 200
    assert response.json == {"ok": True, "database": "connected"}
    assert response.headers["Cache-Control"] == "no-store"


def test_concurrent_complaints_get_distinct_ticket_numbers():
    student = device()
    assert reg(student, "24bm100@iitdh.ac.in").status_code == 200
    with student.session_transaction() as session:
        uid = session["uid"]

    def submit(_):
        client = device()
        with client.session_transaction() as session:
            session["uid"] = uid
        response = post(client, "/api/complaints", {"category": "Water", "description": "No water in the bathroom"})
        assert response.status_code == 200, response.json
        return response.json["code"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(submit, range(16)))
    assert len(set(codes)) == 16
    assert len(student.get("/api/state").json["complaints"]) == 16


def test_failed_image_write_rolls_back_complaint_and_counter():
    student = device()
    assert reg(student, "24bm101@iitdh.ac.in").status_code == 200
    with A.engine.connect() as cx:
        previous = cx.execute(select(A.counters.c.n).where(A.counters.c.hostel == "H2")).scalar_one_or_none()

    def fail_photo(connection, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO complaint_images"):
            raise RuntimeError("Simulated storage failure")

    event.listen(A.engine, "before_cursor_execute", fail_photo)
    try:
        response = post(student, "/api/complaints", {"category": "Water", "description": "Water pipe is broken", "images": [png()]})
        assert response.status_code == 500
    finally:
        event.remove(A.engine, "before_cursor_execute", fail_photo)
    assert student.get("/api/state").json["complaints"] == []
    with A.engine.connect() as cx:
        assert cx.execute(select(A.counters.c.n).where(A.counters.c.hostel == "H2")).scalar_one_or_none() == previous


def test_foreign_keys_are_enforced():
    with pytest.raises(IntegrityError):
        with A.engine.begin() as cx:
            cx.execute(insert(A.images).values(complaint_id=999999, content_type="image/png", data=b"test"))


def test_reinitialization_preserves_complaints_and_photos(monkeypatch):
    student = device()
    assert reg(student, "24bm103@iitdh.ac.in").status_code == 200
    response = post(student, "/api/complaints", {"category": "Water", "description": "Water pipe is broken", "images": [png()]})
    assert response.status_code == 200
    before = student.get("/api/state").json
    A.engine.dispose()
    monkeypatch.setattr(A, "_database_ready", False)
    after = student.get("/api/state").json
    assert before == after
    assert student.get('/api/images/' + str(after["complaints"][0]["images"][0])).status_code == 200


def test_large_upload_returns_json_error():
    student = device()
    assert reg(student, "24bm102@iitdh.ac.in").status_code == 200
    response = student.post("/api/complaints", data='{"images":["' + "a" * 4_000_000 + '"]}', content_type="application/json")
    assert response.status_code == 413
    assert response.is_json and "error" in response.json


def test_initialization_recovers_after_temporary_failure(monkeypatch):
    monkeypatch.setattr(A, "_database_ready", False)
    real_check = A.check_schema
    attempts = []

    def fail_once(cx):
        attempts.append(True)
        if len(attempts) == 1:
            raise OSError("temporary database outage with secret credentials")
        return real_check(cx)

    monkeypatch.setattr(A, "check_schema", fail_once)
    failed = device().get("/api/state")
    assert failed.status_code == 503
    assert "secret credentials" not in failed.get_data(as_text=True)
    assert device().get("/api/state").status_code == 200


def test_bad_admin_scope_does_not_grant_all_access(monkeypatch):
    monkeypatch.setenv("ADMINS", "newadmin@example.com|StrongPass123|TYPO")
    with pytest.raises(A.DatabaseSetupError):
        with A.engine.begin() as cx:
            A.seed_admins(cx)


def test_old_database_is_preserved(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "old.db"))
    try:
        with engine.begin() as cx:
            cx.execute(text("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT)"))
            cx.execute(text("INSERT INTO students VALUES (1, 'Existing student')"))
        with engine.begin() as cx:
            with pytest.raises(A.DatabaseSetupError, match="Back up"):
                A.check_schema(cx)
            assert cx.execute(text("SELECT name FROM students WHERE id=1")).scalar_one() == "Existing student"
    finally:
        engine.dispose()


def import_in_vercel(tmp_path, settings, script):
    env = os.environ.copy()
    for key in ("DATABASE_URL", "TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "SECRET_KEY", "ADMINS", "CORS_ORIGIN"):
        env.pop(key, None)
    env.update(VERCEL="1", SQLITE_PATH=str(tmp_path / "must-not-exist.db"))
    env.update(settings)
    result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).parent,
                            env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "must-not-exist.db").exists()
    return json.loads(result.stdout)


def test_missing_vercel_settings_do_not_break_pages(tmp_path):
    result = import_in_vercel(tmp_path, {}, "import app,json; c=app.app.test_client(); r=c.get('/api/state'); print(json.dumps({'page': c.get('/').status_code, 'api':r.status_code, 'error':r.json['error']}))")
    assert result["page"] == 200 and result["api"] == 503
    assert "SECRET_KEY" in result["error"] and "DATABASE_URL" in result["error"]


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://", "postgresql+psycopg2://"])
def test_postgres_driver_loads_without_connecting_at_import(tmp_path, prefix):
    result = import_in_vercel(tmp_path, {"DATABASE_URL": prefix + "user:password@127.0.0.1:1/hostel",
        "SECRET_KEY": "test-secret", "ADMINS": "admin@example.com|StrongPass123|H1"},
        "import app,json; print(json.dumps({'errors': app.STARTUP_ERRORS, 'driver': app.engine.dialect.driver, 'ready': app._database_ready}))")
    assert result == {"errors": [], "driver": "psycopg2", "ready": False}


def test_vercel_rejects_local_database(tmp_path):
    result = import_in_vercel(tmp_path, {"DATABASE_URL": "sqlite:///hostel.db", "SECRET_KEY": "test-secret",
        "ADMINS": "admin@example.com|StrongPass123|H1"},
        "import app,json; r=app.app.test_client().get('/healthz'); print(json.dumps({'status':r.status_code}))")
    assert result["status"] == 503
