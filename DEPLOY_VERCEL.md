# Deploy Hostel Complaints on Vercel

## What was wrong in the supplied files

- Flask looked for HTML, scripts and styles under `static/`, but every frontend file was at the repository root. That caused page/asset 404 errors. The fixed layout uses `templates/` for pages and `public/` for assets.
- The deployment configuration referred to that missing directory and used the legacy builder. It now uses Vercel's Flask framework support.
- PostgreSQL URLs selected the `psycopg2` driver, but it was missing from requirements. The driver is now included.
- Database connections and schema setup happened while importing the application. A temporary startup failure could disable a Vercel instance until it restarted. Setup now runs on the first API request and can retry.
- Three base64 photos could exceed Vercel's 4.5 MB request limit. Requests now have a 4 MB limit and a browser-side size check.
- Database ticket allocation now uses an atomic upsert. Foreign-key errors are no longer reported as duplicate accounts, and SQLite foreign keys are enabled.

These are issues found in the source. The original Vercel build logs and hosted database were not available.

## 1. Import the correct project folder

The project on this computer is inside the inner `Hostel` folder:

```text
Hostel/
  app.py
  requirements.txt
  vercel.json
  .python-version
  public/
  templates/
```

Push that folder's contents to a Git repository and import the repository in Vercel. If the repository instead contains a surrounding folder, set Vercel's **Root Directory** to the folder containing `app.py`.

- Framework preset: **Flask** (also specified in `vercel.json`).
- Leave Build Command, Install Command and Output Directory at their framework defaults; remove old overrides.
- Keep the folder structure. Do not upload only the HTML files.
- Alternatively, run `vercel` from the directory containing `app.py`, with a current Vercel CLI.

## 2. Connect ONE hosted database

Ask the project owner whether an existing database must be retained. Use that database's connection settings if so; a newly created database starts empty.

### Option A: Turso / libSQL

Create or select a libSQL database in Turso and obtain its URL and token. Add these in **Vercel > Project > Settings > Environment Variables**:

```text
TURSO_DATABASE_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-real-token
```

Do not also set `DATABASE_URL`. This project uses the libSQL driver; it does not use the newer Turso-engine driver.

### Option B: PostgreSQL

Create or select a PostgreSQL database (for example, through Vercel's database integrations), then set:

```text
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

Use the provider's application connection string, including its SSL settings. URL-encode special characters in manually constructed usernames/passwords. Remove both Turso variables. The database user needs permission to create tables on initial setup.

Do not use a local SQLite file or `/tmp` as the production database. Vercel instances do not share persistent local files.

## 3. Set session and secretary settings

Add these for each environment you intend to use (Production and, if needed, Preview):

```text
SECRET_KEY=<long-random-secret>
ADMINS=h1sec@iitdh.ac.in|<strong-password>|H1;h2sec@iitdh.ac.in|<another-password>|H2
```

Generate `SECRET_KEY` on a machine with Python:

```sh
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep the same secret between deployments so sessions remain valid. Replace all placeholders. Secretary passwords must contain 8-128 characters and must not include `|` or `;`. Hostel scope must be exactly `H1`, `H2` or `ALL`.

Leave `CORS_ORIGIN` unset and `public/config.js` unchanged for the normal same-domain deployment. No `DEBUG_STARTUP` setting is needed.

## 4. Deploy and verify

Redeploy after changing environment variables. Open:

1. `/` — student portal; styles and scripts should load.
2. `/healthz` — should return `{"ok":true,"database":"connected"}`. This request initializes tables and configured secretary accounts if needed.
3. `/admin` — sign in using an account from `ADMINS`.
4. Register a test student, submit a complaint with a photo, and confirm the correct secretary can see it.

Use a separate Preview database when testing changes that should not touch live records.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Build cannot find the app | Root Directory must contain `app.py` and `requirements.txt` |
| Build dependency error | Include updated requirements and `.python-version`; inspect the Vercel build log |
| Page works but API returns 503 | Open `/healthz`; check database URL/token, `SECRET_KEY`, `ADMINS`, database access and provider availability |
| Older-schema error | Back up the database and migrate the listed missing columns; do not reset real data |
| Photo request returns 413 | Choose fewer/smaller photos; total JSON request must stay below 4 MB |
| Login does not persist | Use HTTPS on Vercel and keep `SECRET_KEY` stable |
| Secretary cannot log in | Confirm `ADMINS` format, scope and password, then redeploy |

## References

- [Vercel Flask deployment and public assets](https://vercel.com/docs/frameworks/backend/flask)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel request size limits](https://vercel.com/docs/functions/limitations)
- [Turso SQLAlchemy libSQL driver](https://github.com/tursodatabase/sqlalchemy-libsql)
