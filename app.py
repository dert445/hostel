"""Hostel Complaints: central API. Every student and every secretary uses this ONE database.
Local dev:  python app.py        Cloud:  gunicorn app:app  with DATABASE_URL, SECRET_KEY, ADMINS set (see README)."""
import base64, os, re, time
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, Response, jsonify, request, session, send_from_directory
from sqlalchemy import (Column, ForeignKey, Integer, LargeBinary, MetaData, String, Table, Text, create_engine, func, insert, select, update)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

def is_unique_error(e):   # Postgres/SQLite raise IntegrityError; the Turso (libSQL) driver raises a plain ValueError with the same message
    return isinstance(e, IntegrityError) or "UNIQUE constraint failed" in str(e)
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB_URL = os.environ.get("DATABASE_URL", "")            # cloud Postgres URL; empty = local SQLite file
TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").strip()      # e.g. libsql://hostel-yourname.turso.io
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
PROD = bool(DB_URL or TURSO_URL)
ON_VERCEL = bool(os.environ.get("VERCEL"))
STARTUP_ERRORS = []   # on Vercel, startup problems are recorded and shown (with DEBUG_STARTUP=1) instead of a blank 500
def startup_problem(msg):
    if not ON_VERCEL: raise RuntimeError(msg)
    STARTUP_ERRORS.append(msg)
if TURSO_URL and not TURSO_TOKEN:
    startup_problem("TURSO_AUTH_TOKEN is missing. Create a token in Turso (turso db tokens create <db-name>) and add it, then redeploy.")
if ON_VERCEL and not (DB_URL or TURSO_URL):   # Vercel's disk is read-only, so the plain SQLite file fallback cannot work there
    startup_problem("TURSO_DATABASE_URL is missing. Add your Turso database URL (libsql://...) in Vercel > Settings > Environment Variables, then redeploy.")
if DB_URL.startswith("postgres://"): DB_URL = "postgresql://" + DB_URL[len("postgres://"):]
if DB_URL.startswith("postgresql://"): DB_URL = "postgresql+psycopg2://" + DB_URL[len("postgresql://"):]
try:
    if TURSO_URL:     # Turso (libSQL) over the network: needs the sqlalchemy-libsql package
        _host = re.sub(r"^(libsql|https|wss|http|ws)://", "", TURSO_URL).rstrip("/")
        engine = create_engine(f"sqlite+libsql://{_host}?secure=true", connect_args={"auth_token": TURSO_TOKEN}, poolclass=NullPool)
    else:
        engine = create_engine(DB_URL or "sqlite:///" + os.environ.get("SQLITE_PATH", os.path.join(BASE, "hostel.db")),
                               pool_pre_ping=True, **({"poolclass": NullPool} if ON_VERCEL else {}))   # serverless: no connection pool kept between requests
except Exception as e:
    if not ON_VERCEL: raise
    engine = create_engine("sqlite://")   # dummy so the module can load; real error is reported below
    STARTUP_ERRORS.append("Could not set up the database (" + type(e).__name__ + "). Check TURSO_DATABASE_URL (libsql://...) and that requirements.txt has sqlalchemy-libsql and libsql-experimental.")

SECRET = os.environ.get("SECRET_KEY")
if PROD and not SECRET: startup_problem("SECRET_KEY is missing. Add a long random string in the environment variables, then redeploy.")
CORS = [o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGIN", "").split(",") if o.strip()]   # only if the frontend is hosted on a different domain

app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="")
app.secret_key = SECRET or "dev-only-secret"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=PROD or bool(CORS),
                  SESSION_COOKIE_SAMESITE="None" if CORS else "Lax", MAX_CONTENT_LENGTH=8 * 1024 * 1024, SEND_FILE_MAX_AGE_DEFAULT=0)
if PROD: app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

WINGS = {"H1": list("ABCDE"), "H2": list("ABCDE")}
CATEGORIES = ["Water", "Wi-Fi", "Electrical", "Cleanliness", "Furniture", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
WING_ROOMS = {"A": (1, 4), "B": (5, 10), "C": (11, 16), "D": (17, 24), "E": (25, 32)}   # room numbers on each floor, per wing
def valid_room(floor, wing, room):
    lo, hi = WING_ROOMS[wing]
    return room in [("G" if floor == 0 else str(floor)) + f"{i:02d}" for i in range(lo, hi + 1)]
EMAIL_RE = re.compile(r"^[a-z0-9]{5,12}@iitdh\.ac\.in$")
WA_RE = re.compile(r"^\+91[6-9]\d{9}$")
IMG_RE = re.compile(r"^data:(image/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$")
MAGIC = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n"}

# ---------- tables ----------
meta = MetaData()
students = Table("students", meta, Column("id", Integer, primary_key=True), Column("name", String(80), nullable=False),
    Column("roll", String(20), unique=True, nullable=False), Column("email", String(120), unique=True, nullable=False),
    Column("whatsapp", String(20), nullable=False), Column("hostel", String(4), nullable=False), Column("wing", String(2), nullable=False),
    Column("floor", Integer, nullable=False), Column("room", String(8), nullable=False), Column("pw_hash", String(300), nullable=False),
    Column("created_at", String(40), nullable=False))
admins = Table("admins", meta, Column("id", Integer, primary_key=True), Column("email", String(120), unique=True, nullable=False),
    Column("pw_hash", String(300), nullable=False), Column("hostel", String(4), nullable=False))     # hostel: H1, H2 or ALL
complaints = Table("complaints", meta, Column("id", Integer, primary_key=True), Column("code", String(20), unique=True, nullable=False),
    Column("student_id", Integer, ForeignKey("students.id"), nullable=False, index=True), Column("student_name", String(80), nullable=False),
    Column("roll", String(20), nullable=False), Column("hostel", String(4), nullable=False, index=True), Column("wing", String(2), nullable=False),
    Column("floor", Integer, nullable=False), Column("room", String(8), nullable=False), Column("category", String(20), nullable=False),
    Column("description", Text, nullable=False), Column("status", String(20), nullable=False, default="Pending"),
    Column("priority", String(10), nullable=False, default="Medium"), Column("assigned_to", String(60)), Column("remarks", Text),
    Column("prev", String(20)), Column("created_at", String(40), nullable=False), Column("updated_at", String(40), nullable=False),
    Column("resolved_at", String(40)))
images = Table("complaint_images", meta, Column("id", Integer, primary_key=True),
    Column("complaint_id", Integer, ForeignKey("complaints.id"), nullable=False, index=True),
    Column("content_type", String(20), nullable=False), Column("data", LargeBinary, nullable=False))
counters = Table("counters", meta, Column("hostel", String(4), primary_key=True), Column("n", Integer, nullable=False))

def seed_admins():
    spec = os.environ.get("ADMINS") or ("" if PROD else "sec@h1.edu|secretary123|ALL")   # format: email|password|H2;email|password|H1
    if not spec: raise RuntimeError("Set ADMINS, e.g. h2sec@iitdh.ac.in|StrongPassword|H2")
    for part in filter(None, (p.strip() for p in spec.split(";"))):
        try: email, pw, host = [x.strip() for x in part.split("|")]
        except ValueError: raise RuntimeError("ADMINS must look like email|password|H1 (separate accounts with ;). Check for an extra | or ; in a password.")
        h = host.upper() if host.upper() in ("H1", "H2") else "ALL"
        try:
            with engine.begin() as cx:
                row = cx.execute(select(admins.c.id, admins.c.pw_hash, admins.c.hostel).where(admins.c.email == email.lower())).first()
                if row is None:
                    cx.execute(insert(admins).values(email=email.lower(), pw_hash=generate_password_hash(pw), hostel=h))
                elif row.hostel != h or not check_password_hash(row.pw_hash, pw):   # write only when something changed
                    cx.execute(update(admins).where(admins.c.id == row.id).values(pw_hash=generate_password_hash(pw), hostel=h))
        except Exception as e:
            if not is_unique_error(e): raise   # another server instance created this account at the same moment: fine

# ---------- helpers ----------
def now(): return datetime.now(timezone.utc).isoformat()
def err(msg, code=400): return jsonify(error=msg), code
def body():
    d = request.get_json(silent=True) if request.is_json else None      # JSON only: blocks cross-site form posts
    return d if isinstance(d, dict) else {}
FAILS = {}
def locked(k):
    FAILS[k] = [t for t in FAILS.get(k, []) if t > time.time() - 600]; return len(FAILS[k]) >= 8
def failed(k): FAILS.setdefault(k, []).append(time.time())

def student_only(f):
    @wraps(f)
    def w(*a, **k): return f(*a, **k) if session.get("uid") else err("Please log in.", 401)
    return w
def admin_only(f):
    @wraps(f)
    def w(*a, **k): return f(*a, **k) if session.get("admin") else err("Admin login required.", 401)
    return w
def scoped(q):                                                           # a secretary only sees their own hostel unless ALL
    h = (session.get("admin") or {}).get("hostel", "ALL")
    return q if h == "ALL" else q.where(complaints.c.hostel == h)

def img_ids(cx, ids):
    out = {}
    if ids:
        for i, cid in cx.execute(select(images.c.id, images.c.complaint_id).where(images.c.complaint_id.in_(ids)).order_by(images.c.id)): out.setdefault(cid, []).append(i)
    return out
def cj(r, imgs, wa=None):
    return dict(n=r.id, code=r.code, studentId=str(r.student_id), studentName=r.student_name, roll=r.roll, hostel=r.hostel, wing=r.wing,
        floor=r.floor, room=r.room, category=r.category, description=r.description, status=r.status, priority=r.priority,
        assignedTo=r.assigned_to, remarks=r.remarks, prev=r.prev, createdAt=r.created_at, updatedAt=r.updated_at, resolvedAt=r.resolved_at,
        images=imgs.get(r.id, []), whatsapp=wa)

@app.before_request
def origin_check():
    o = request.headers.get("Origin")
    if request.method == "POST" and o and o.rstrip("/") not in CORS and o.rstrip("/") != request.host_url.rstrip("/"): return err("Blocked origin.", 403)
@app.after_request
def cors(resp):
    o = (request.headers.get("Origin") or "").rstrip("/")
    if o and o in CORS:
        resp.headers.update({"Access-Control-Allow-Origin": o, "Access-Control-Allow-Credentials": "true", "Vary": "Origin",
                             "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"})
    return resp

# ---------- pages ----------
@app.get("/")
def student_page(): return send_from_directory(app.static_folder, "student.html")
@app.get("/admin")
def admin_page(): return send_from_directory(app.static_folder, "admin.html")
@app.get("/healthz")
def health(): return jsonify(ok=True)

# ---------- state + change detection (the frontend polls /api/ping every few seconds) ----------
EMPTY = dict(students=[], complaints=[], session=None, adminSession=None)
@app.get("/api/state")
def state():
    with engine.connect() as cx:
        if request.args.get("as") == "admin":
            a = session.get("admin")
            if not a: return jsonify(EMPTY)
            rows = cx.execute(scoped(select(complaints, students.c.whatsapp).select_from(complaints.join(students)).order_by(complaints.c.id))).all()
            im = img_ids(cx, [r.id for r in rows])
            return jsonify(dict(EMPTY, complaints=[cj(r, im, r.whatsapp) for r in rows], adminSession=dict(role="secretary", hostel=a["hostel"], email=a["email"])))
        uid = session.get("uid")
        me = cx.execute(select(students).where(students.c.id == uid)).first() if uid else None
        if not me:
            session.pop("uid", None); return jsonify(EMPTY)
        rows = cx.execute(select(complaints).where(complaints.c.student_id == me.id).order_by(complaints.c.id)).all()
        im = img_ids(cx, [r.id for r in rows])
        s = dict(id=str(me.id), name=me.name, roll=me.roll, hostel=me.hostel, whatsapp=me.whatsapp, wing=me.wing, floor=me.floor, room=me.room, email=me.email)
        return jsonify(dict(EMPTY, students=[s], complaints=[cj(r, im) for r in rows], session=dict(role="student", id=str(me.id))))

@app.get("/api/ping")
def ping():
    q = select(func.count(complaints.c.id), func.max(complaints.c.updated_at))
    if request.args.get("as") == "admin":
        if not session.get("admin"): return jsonify(v="0")
        q = scoped(q)
    else:
        if not session.get("uid"): return jsonify(v="0")
        q = q.where(complaints.c.student_id == session["uid"])
    with engine.connect() as cx: n, m = cx.execute(q).one()
    return jsonify(v=f"{n}:{m}")

# ---------- student auth ----------
@app.post("/api/register")
def register():
    d = body(); name = str(d.get("name", "")).strip(); email = str(d.get("email", "")).strip().lower(); pw = str(d.get("password", ""))
    wa = str(d.get("whatsapp", "")).strip(); hostel = d.get("hostel"); wing = d.get("wing"); room = str(d.get("room", ""))
    try: floor = int(d.get("floor"))
    except (TypeError, ValueError): return err("Choose your floor.")
    if not 1 <= len(name) <= 80: return err("Enter your full name.")
    if hostel not in WINGS or wing not in WINGS[hostel] or not 0 <= floor <= 8 or not valid_room(floor, wing, room):
        return err("Choose a valid hostel, wing, floor and room.")
    if not WA_RE.match(wa): return err("Enter a valid 10-digit WhatsApp number.")
    if not EMAIL_RE.match(email): return err("Use your institute email in the form rollno@iitdh.ac.in.")
    if not 8 <= len(pw) <= 128: return err("Password must be at least 8 characters.")
    try:
        with engine.begin() as cx:
            uid = cx.execute(insert(students).values(name=name, roll=email.split("@")[0].upper(), email=email, whatsapp=wa, hostel=hostel, wing=wing,
                floor=floor, room=room, pw_hash=generate_password_hash(pw), created_at=now())).inserted_primary_key[0]
    except Exception as e:
        if not is_unique_error(e): raise
        return err("An account with this email or roll number already exists.", 409)
    session["uid"] = uid
    return jsonify(ok=True)

@app.post("/api/login")
def login():
    d = body(); email = str(d.get("email", "")).strip().lower(); key = f"s:{request.remote_addr}:{email}"
    if locked(key): return err("Too many attempts. Try again in 10 minutes.", 429)
    with engine.connect() as cx: r = cx.execute(select(students).where(students.c.email == email)).first()
    if not r or not check_password_hash(r.pw_hash, str(d.get("password", ""))):
        failed(key); return err("Email or password is incorrect.", 401)
    session["uid"] = r.id
    return jsonify(ok=True)

@app.post("/api/logout")
def logout(): session.pop("uid", None); return jsonify(ok=True)

# ---------- admin auth ----------
@app.post("/api/admin/login")
def admin_login():
    d = body(); email = str(d.get("email", "")).strip().lower(); key = f"a:{request.remote_addr}:{email}"
    if locked(key): return err("Too many attempts. Try again in 10 minutes.", 429)
    with engine.connect() as cx: r = cx.execute(select(admins).where(admins.c.email == email)).first()
    if not r or not check_password_hash(r.pw_hash, str(d.get("password", ""))):
        failed(key); return err("Email or password is incorrect.", 401)
    session["admin"] = dict(email=r.email, hostel=r.hostel)
    return jsonify(ok=True)

@app.post("/api/admin/logout")
def admin_logout(): session.pop("admin", None); return jsonify(ok=True)

# ---------- complaints ----------
def decode_images(raw):
    if not isinstance(raw, list) or len(raw) > 3: raise ValueError("You can attach up to 3 photos.")
    out = []
    for s in raw:
        m = IMG_RE.match(str(s))
        if not m: raise ValueError("Photos must be JPEG, PNG or WebP.")
        try: data = base64.b64decode(m.group(2), validate=True)
        except Exception: raise ValueError("A photo could not be read.")
        ok = data.startswith(MAGIC[m.group(1)]) if m.group(1) in MAGIC else data[:4] == b"RIFF" and data[8:12] == b"WEBP"
        if not ok or len(data) > 1_500_000: raise ValueError("Each photo must be a valid image under 1.5 MB.")
        out.append((m.group(1), data))
    return out

@app.post("/api/complaints")
@student_only
def create_complaint():
    d = body(); cat = d.get("category"); desc = str(d.get("description", "")).strip()
    if cat not in CATEGORIES: return err("Choose a category.")
    if not 10 <= len(desc) <= 500: return err("Describe the problem in 10 to 500 characters.")
    try: pics = decode_images(d.get("images") or [])
    except ValueError as e: return err(str(e))
    for _ in range(3):                                   # retry if two students grab the same ticket number at once
        try:
            with engine.begin() as cx:
                me = cx.execute(select(students).where(students.c.id == session["uid"])).first()
                if not me: return err("Please log in.", 401)
                row = cx.execute(select(counters.c.n).where(counters.c.hostel == me.hostel).with_for_update()).first()
                n = (row[0] if row else 0) + 1
                if row: cx.execute(update(counters).where(counters.c.hostel == me.hostel).values(n=n))
                else: cx.execute(insert(counters).values(hostel=me.hostel, n=n))
                code = f"{me.hostel}-{n:04d}"; t = now()
                cid = cx.execute(insert(complaints).values(code=code, student_id=me.id, student_name=me.name, roll=me.roll, hostel=me.hostel,
                    wing=me.wing, floor=me.floor, room=me.room, category=cat, description=desc, status="Pending", priority="Medium",
                    created_at=t, updated_at=t)).inserted_primary_key[0]
                for ct, data in pics: cx.execute(insert(images).values(complaint_id=cid, content_type=ct, data=data))
            return jsonify(ok=True, code=code, id=cid)
        except Exception as e:
            if not is_unique_error(e): raise
            continue
    return err("Could not save right now. Please try again.", 503)

@app.post("/api/complaints/<int:cid>/resolve")
@student_only
def resolve(cid):
    with engine.begin() as cx:
        c = cx.execute(select(complaints).where(complaints.c.id == cid, complaints.c.student_id == session["uid"])).first()
        if not c: return err("Complaint not found.", 404)
        if c.status == "Rejected": return err("A rejected complaint can't be resolved.")
        t = now(); w = update(complaints).where(complaints.c.id == cid)
        if body().get("resolved"):
            if c.status != "Resolved": cx.execute(w.values(prev=c.status, status="Resolved", resolved_at=t, updated_at=t))
        elif c.status == "Resolved":
            cx.execute(w.values(status=c.prev if c.prev in ("Pending", "In Progress") else "Pending", prev=None, resolved_at=None, updated_at=t))
    return jsonify(ok=True)

@app.post("/api/admin/complaints/<int:cid>")
@admin_only
def admin_update(cid):
    d = body(); vals = {}
    with engine.begin() as cx:
        c = cx.execute(scoped(select(complaints).where(complaints.c.id == cid))).first()
        if not c: return err("Complaint not found.", 404)
        if "status" in d:
            if d["status"] not in ("Pending", "In Progress", "Rejected"): return err("Invalid status.")
            if c.status == "Resolved" and d["status"] != "Resolved": return err("Only the student can change a resolved complaint.")
            vals["status"] = d["status"]
        if "priority" in d:
            if d["priority"] not in PRIORITIES: return err("Invalid priority.")
            vals["priority"] = d["priority"]
        if "assigned_to" in d: vals["assigned_to"] = (str(d["assigned_to"] or "").strip()[:60]) or None
        if "remarks" in d: vals["remarks"] = (str(d["remarks"] or "").strip()[:1000]) or None
        if vals.get("status", c.status) == "Rejected" and not vals.get("remarks", c.remarks): return err("Add a reason in the remarks when rejecting.")
        vals["updated_at"] = now()
        cx.execute(update(complaints).where(complaints.c.id == cid).values(**vals))
    return jsonify(ok=True)

@app.get("/api/images/<int:iid>")
def image(iid):
    with engine.connect() as cx:
        r = cx.execute(select(images.c.content_type, images.c.data, complaints.c.student_id, complaints.c.hostel).select_from(images.join(complaints)).where(images.c.id == iid)).first()
    a = session.get("admin")
    if not r or not ((session.get("uid") and session["uid"] == r.student_id) or (a and a["hostel"] in ("ALL", r.hostel))): return err("Not found.", 404)
    return Response(r.data, mimetype=r.content_type, headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})

@app.errorhandler(Exception)
def on_error(e):                                    # API calls always get a JSON message, never an HTML error page
    if not request.path.startswith("/api/"): return e if isinstance(e, HTTPException) else Response("Server error", 500)
    if isinstance(e, HTTPException): return err(e.description or e.name, e.code)
    app.logger.exception("API error")
    return err("The server hit an error. Check the server logs (terminal or cloud dashboard) for details.", 500)

def check_schema():                                 # an old hostel.db from an earlier version would otherwise cause confusing errors
    from sqlalchemy import inspect
    insp = inspect(engine)
    for t in meta.sorted_tables:
        if insp.has_table(t.name):
            have = {c["name"] for c in insp.get_columns(t.name)}
            missing = [c.name for c in t.columns if c.name not in have]
            if missing: raise RuntimeError(f"Existing database is from an older version (table '{t.name}' lacks {missing}). "
                                           "Delete hostel.db (local testing) or reset the cloud database, then restart.")
if not STARTUP_ERRORS:
    try:
        check_schema()
        meta.create_all(engine)
        seed_admins()
    except Exception as e:
        if not ON_VERCEL: raise
        STARTUP_ERRORS.append(type(e).__name__ + ": " + (str(e).splitlines() or [""])[0][:200])
if STARTUP_ERRORS:
    for _m in STARTUP_ERRORS: app.logger.error("STARTUP PROBLEM: %s", _m)
    @app.before_request
    def _startup_failed():
        txt = ("Startup problem:\n- " + "\n- ".join(STARTUP_ERRORS)) if os.environ.get("DEBUG_STARTUP") == "1" \
              else "The server is not configured correctly. Check the deployment logs."
        return Response(txt, 500, mimetype="text/plain")
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
