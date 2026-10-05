# Hostel Complaints

<<<<<<< HEAD
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
=======
A complaint-management system for college hostels (H1 and H2). Students log in with their institute email,
report problems with photos, and track progress. The hostel secretary manages everything from one dashboard.

Every student and every secretary uses **one backend and one database**, so a complaint filed on any device
appears on the secretary's dashboard automatically. Nothing is stored in the browser except a login cookie.

## Features
- **Students:** register with `rollno@iitdh.ac.in`, hostel, wing, floor, room and WhatsApp number (rooms depend on the wing); submit complaints with up to 3 photos; see ticket ID, status, assigned person and remarks; tick **Resolved** when fixed
- **Secretary dashboard:** search, filter by hostel / wing / floor / category / status, open any complaint, change status, set priority, assign, add remarks, reject with a reason, open WhatsApp
- **Hostel council** page with photos
- **Accounts per hostel:** an H2 Secretary only sees H2 complaints (or use `ALL`)
- Automatic refresh (the dashboard checks for changes every 8 seconds)

## Tech
Python 3.10+, Flask, SQLAlchemy (SQLite for local testing, PostgreSQL in the cloud), plain HTML/CSS/JavaScript frontend served by Flask.

## Run it on your computer
    python -m venv venv
    venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
    pip install -r requirements.txt
    python app.py

- Students: http://127.0.0.1:5000
- Secretary: http://127.0.0.1:5000/admin   (local test login: `sec@h1.edu` / `secretary123`)

Open the site through this address, not through VS Code Live Server or a static host: the pages need the Flask API.
Local mode stores data in `hostel.db` (ignored by Git).

## Deploy to the cloud (Render example)
1. Push this repository to GitHub.
2. On Render choose **New > Blueprint** and select the repo. `render.yaml` creates the web service and a Postgres database.
3. In the Render dashboard set `ADMINS`, for example `h2sec@iitdh.ac.in|YourStrongPassword|H2`
   (format `email|password|hostel`, separate several with `;`, use `ALL` to see both hostels).
4. Open the URL Render gives you. Students use it as is; the secretary opens `/admin`.

GitHub Pages, Netlify and similar static hosts cannot run this app by themselves, because it needs the Flask backend.
Any host that runs Python and Postgres works (Railway, Fly.io, Heroku, a VPS): set the variables below and run `gunicorn app:app`.

## Environment variables
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string. Setting it switches the app to cloud mode |
| `SECRET_KEY` | Long random string (required in cloud mode) |
| `ADMINS` | Secretary accounts, `email\|password\|H1/H2/ALL`, separated by `;` (required in cloud mode) |
| `CORS_ORIGIN` | Only if the website is hosted on a different domain than the API (also set `API_BASE` in `static/config.js`) |
| `SQLITE_PATH` | Optional path for the local SQLite file |

See `.env.example`. **Never commit real passwords or database URLs.**

## Project structure
    app.py                 Flask API, database tables, rules
    static/                the website (student.html, admin.html, shared.css, *.js, images)
    tests/test_api.py      automated tests
    render.yaml, Procfile  cloud deployment
    .github/workflows/     runs the tests on every push

## Tests
    pip install pytest pillow
    pytest -q

## Security notes
- Passwords are stored hashed. Secretary passwords live only in the host's environment settings.
- The default `sec@h1.edu` login exists only in local mode (no `DATABASE_URL`).
- Student emails are format-checked only; there is no email confirmation link yet.
- Photos are stored inside the database. Back up the database before relying on it.
- `static/` includes photos of real people (council members). Remove or replace them before making a repository public.

## License
Add a `LICENSE` file of your choice before sharing the code publicly.
>>>>>>> 36bd082e4b9b1e7e38d730aba57f2d1feede9366
