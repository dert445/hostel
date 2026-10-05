# Hostel Complaints

A Flask website for H1 and H2 hostel complaints. Students register with their institute email, submit complaints with up to three photos, and mark problems resolved. Secretaries manage complaints within their assigned hostel.

All devices use one API and one database. Local development uses SQLite. Vercel requires a hosted Turso/libSQL or PostgreSQL database.

## Deploy on Vercel

Follow [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md). Import the folder containing `app.py`, `requirements.txt` and `vercel.json`. Keep the `public/` and `templates/` directories intact.

This is a Python backend application; uploading just the HTML files will not run it.

## Run locally (Python 3.12)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

On macOS/Linux, activate with `source .venv/bin/activate`.

- Student portal: http://127.0.0.1:5000
- Secretary portal: http://127.0.0.1:5000/admin
- Local test secretary: `sec@h1.edu` / `secretary123`
- Database readiness: http://127.0.0.1:5000/healthz

Leave cloud database variables unset for local testing. The first API request creates `hostel.db` and the tables. The default secretary is only available in local mode. The native Turso driver runs on Linux/macOS (including Vercel); Windows development uses SQLite or PostgreSQL.

## Environment variables

| Variable | Purpose |
|---|---|
| `TURSO_DATABASE_URL` | Hosted libSQL URL, such as `libsql://your-db.turso.io` |
| `TURSO_AUTH_TOKEN` | Required with the Turso URL |
| `DATABASE_URL` | PostgreSQL URL; use instead of both Turso settings |
| `SECRET_KEY` | Stable random session-signing secret, required for hosting |
| `ADMINS` | `email\|password\|H1`, `H2`, or `ALL`; separate accounts with `;` |
| `SQLITE_PATH` | Optional local SQLite path; not supported for Vercel persistence |
| `CORS_ORIGIN` | Only for a separate frontend domain; also update `public/config.js` |

`.env.example` documents the values. The application does not automatically load `.env` files; set variables in your shell or hosting dashboard. Never commit real credentials.

## Database behavior

Tables and configured secretary accounts initialize on the first API request. Initialization is serialized and can retry after a temporary connection failure. Ticket counters update atomically; complaint details, photos and the counter commit together. SQLite foreign keys are enabled. Existing compatible records are retained.

An incompatible older schema returns a setup error naming missing columns. Back up that database and create a migration based on its actual schema; do not delete or reset real records. No existing cloud database was supplied with this project, so live connectivity and old-data migration need checking against the owner's database.

`ADMINS` creates or updates listed accounts. Removing an entry does not delete a previously created account. Student emails are format-checked, not verified by email. Login attempt limits are per Python process and are not shared across Vercel instances.

## Project structure

```text
app.py                 Flask API and database setup
public/                CSS, JavaScript and council images (Vercel CDN)
templates/             Student and secretary HTML pages
requirements.txt       Runtime packages
.python-version        Python 3.12 for Vercel
vercel.json            Flask deployment configuration
.env.example           Placeholder settings
DEPLOY_VERCEL.md        Deployment and troubleshooting steps
test_api.py            Student/secretary workflow tests
test_deployment.py     Deployment, concurrency and persistence tests
```

## Tests

```powershell
pip install pytest pillow
python -m pytest -q
```

Tests use temporary SQLite databases and do not use production credentials. PostgreSQL import/driver checks run without connecting to a remote server. Live PostgreSQL/Turso integration must be verified after setting up the hosted database.
