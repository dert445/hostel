# Deploy on Vercel with Turso

1. Turso: create a database, then get its URL and a token.
   Dashboard: turso.tech > Databases > your DB > copy the URL (libsql://...) > Generate Token.
   CLI:  turso db show --url <db-name>   and   turso db tokens create <db-name>
2. Push this folder's contents to the ROOT of a GitHub repo (app.py, vercel.json, requirements.txt, static/ at top level).
3. Vercel > Add New > Project > import the repo. Framework Preset: Other.
4. Environment Variables:
   - TURSO_DATABASE_URL = libsql://<db>-<user>.turso.io
   - TURSO_AUTH_TOKEN   = the token
   - SECRET_KEY         = a long random string
   - ADMINS             = h1sec@iitdh.ac.in|StrongPass1|H1;h2sec@iitdh.ac.in|StrongPass2|H2
   - DEBUG_STARTUP      = 1   (temporary; shows startup errors on the page, delete when the site works)
5. Deploy, then Redeploy after any variable change.

Photos are stored in the database as binary data.
