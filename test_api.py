"""End-to-end checks: several separate "devices" (cookie jars) talk to ONE database."""
import base64, io, os, sys, tempfile
<<<<<<< HEAD
for key in ("DATABASE_URL", "TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN", "VERCEL", "SECRET_KEY", "CORS_ORIGIN"):
    os.environ.pop(key, None)
os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMINS"] = "h2sec@iitdh.ac.in|SecPass-2026|H2;h1sec@iitdh.ac.in|SecPass-1111|H1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
=======
os.environ.pop("DATABASE_URL", None)
os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["ADMINS"] = "h2sec@iitdh.ac.in|SecPass-2026|H2;h1sec@iitdh.ac.in|SecPass-1111|H1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
>>>>>>> 36bd082e4b9b1e7e38d730aba57f2d1feede9366
import app as A

def device(): return A.app.test_client()
def post(c, url, data=None): return c.post(url, json=data or {})
def reg(c, email, hostel="H2", wing="B", floor=2, room="205"):
    return post(c, "/api/register", dict(name="Test " + email[:5], email=email, password="demo12345", whatsapp="+919876543210",
                                         hostel=hostel, wing=wing, floor=floor, room=room))
def png():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (20, 20), (200, 30, 30)).save(b, "PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()

def test_complaints_from_different_devices_reach_the_same_secretary():
    a, b, c = device(), device(), device()
    assert reg(a, "24bm001@iitdh.ac.in").status_code == 200
    assert reg(b, "24ce002@iitdh.ac.in", room="206").status_code == 200
    assert reg(c, "24ee003@iitdh.ac.in", hostel="H1", wing="A", floor=3, room="301").status_code == 200
    ra = post(a, "/api/complaints", dict(category="Water", description="Water leakage in the bathroom", images=[png()])).get_json()
    rb = post(b, "/api/complaints", dict(category="Electrical", description="Fan is not working at all")).get_json()
    rc = post(c, "/api/complaints", dict(category="Wi-Fi", description="No wifi on the third floor")).get_json()
    assert ra["code"].startswith("H2-") and rb["code"].startswith("H2-") and rc["code"].startswith("H1-")
    sec_h2, sec_h1 = device(), device()
    assert post(sec_h2, "/api/admin/login", dict(email="h2sec@iitdh.ac.in", password="SecPass-2026")).status_code == 200
    assert post(sec_h1, "/api/admin/login", dict(email="h1sec@iitdh.ac.in", password="SecPass-1111")).status_code == 200
    h2 = sec_h2.get("/api/state?as=admin").get_json()["complaints"]
    assert {x["code"] for x in h2} == {ra["code"], rb["code"]}
    assert [x["code"] for x in sec_h1.get("/api/state?as=admin").get_json()["complaints"]] == [rc["code"]]
    img = next(x for x in h2 if x["code"] == ra["code"])["images"][0]
    assert sec_h2.get(f"/api/images/{img}").status_code == 200 and a.get(f"/api/images/{img}").status_code == 200
    assert b.get(f"/api/images/{img}").status_code == 404 and sec_h1.get(f"/api/images/{img}").status_code == 404

def test_admin_workflow_and_student_resolve_rules():
    s, sec = device(), device()
    reg(s, "24bm010@iitdh.ac.in", room="207")
    cid = post(s, "/api/complaints", dict(category="Other", description="Door lock is broken")).get_json()["id"]
    assert post(sec, f"/api/admin/complaints/{cid}", {"status": "In Progress"}).status_code == 401      # not logged in
    post(sec, "/api/admin/login", dict(email="h2sec@iitdh.ac.in", password="SecPass-2026"))
    assert post(sec, f"/api/admin/complaints/{cid}", {"status": "Rejected"}).status_code == 400         # reason required
    assert post(sec, f"/api/admin/complaints/{cid}", {"status": "In Progress", "priority": "Urgent", "assigned_to": "Warden", "remarks": "On it"}).status_code == 200
    mine = s.get("/api/state?as=student").get_json()["complaints"][0]
    assert (mine["status"], mine["priority"], mine["assignedTo"], mine["remarks"]) == ("In Progress", "Urgent", "Warden", "On it")
    assert post(s, f"/api/complaints/{cid}/resolve", {"resolved": True}).status_code == 200
    assert post(sec, f"/api/admin/complaints/{cid}", {"status": "Pending"}).status_code == 400          # only the student can reopen

def test_registration_rules():
    c = device()
    assert reg(c, "someone@gmail.com").status_code == 400                                              # must be @iitdh.ac.in
    assert reg(c, "24bm020@iitdh.ac.in", wing="A", room="205").status_code == 400                      # wing A is rooms 1-4
    assert reg(c, "24bm021@iitdh.ac.in", wing="A", room="204").status_code == 200
    assert reg(device(), "24bm021@iitdh.ac.in", wing="A", room="204").status_code == 409                # duplicate account

def test_room_ranges_per_wing():
    for wing, (lo, hi) in A.WING_ROOMS.items():
        assert A.valid_room(2, wing, f"2{lo:02d}") and A.valid_room(2, wing, f"2{hi:02d}")
        assert not A.valid_room(2, wing, f"2{hi + 1:02d}")
