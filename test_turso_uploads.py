"""Photo upload regression for libSQL's missing DB-API Binary constructor."""
import base64
import sqlite3

import pytest
from sqlalchemy import create_engine, event, text

from test_api import A, device, png, post, reg


class WithoutBinary:
    """Reproduce libSQL's missing Binary helper using a disposable SQLite DB."""

    def __getattr__(self, name):
        if name == "Binary":
            raise AttributeError("module 'libsql_experimental' has no attribute 'Binary'")
        return getattr(sqlite3, name)


@pytest.fixture(params=["missing-binary", "native-libsql"])
def photo_database(request, tmp_path, monkeypatch):
    path = (tmp_path / "photos.db").as_posix()
    if request.param == "native-libsql":
        pytest.importorskip("libsql_experimental", reason="Native libSQL requires Linux/macOS")
        pytest.importorskip("sqlalchemy_libsql")
        engine = create_engine("sqlite+libsql:///" + path)
    else:
        engine = create_engine("sqlite:///" + path, module=WithoutBinary())
        engine.dialect.driver = "libsql"
    event.listen(engine, "connect", A.sqlite_constraints)
    monkeypatch.setattr(A, "engine", engine)
    monkeypatch.setattr(A, "_database_ready", False)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.parametrize("photo_count", [0, 1, 3])
def test_complaint_photos_round_trip(photo_database, photo_count):
    student = device()
    assert reg(student, "24bm200@iitdh.ac.in").status_code == 200
    picture = png()
    raw = base64.b64decode(picture.split(",", 1)[1])
    response = post(student, "/api/complaints", {
        "category": "Water", "description": "Water pipe is leaking in the bathroom",
        "images": [picture] * photo_count,
    })
    assert response.status_code == 200, response.json
    complaint = student.get("/api/state").json["complaints"][0]
    assert complaint["code"] == "H2-0001"
    assert len(complaint["images"]) == photo_count
    for image_id in complaint["images"]:
        photo = student.get(f"/api/images/{image_id}")
        assert photo.status_code == 200
        assert photo.mimetype == "image/png"
        assert photo.data == raw
        assert device().get(f"/api/images/{image_id}").status_code == 404
    with photo_database.connect() as cx:
        # Keep the existing BLOB storage format; no migration or base64 column.
        assert cx.execute(text("SELECT typeof(data) FROM complaint_images")).scalars().all() == ["blob"] * photo_count
