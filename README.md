# TrustVault — secure document sharing with an audit trail

TrustVault is a hiring-challenge implementation of a document platform with named per-document grants, server-side access checks, a searchable document catalogue, validated uploads, and an audit trail with a tamper-evident hash chain.

> **Challenge/demo software, not a production document-management service.** Review `THREATS.md` for accepted limitations. Do not upload real confidential data. Change all secrets before deployment.

## Current features

- Session-based login, public sign-up that creates normal document-owning accounts and then requires explicit sign-in, and three internal roles: `admin`, `owner`, and `viewer`. Anonymous visitors are redirected to the login screen before they can reach the workspace or any document route.
- Public registration always creates a normal `owner` account; the submitted form cannot set a privileged role. Admins can provision normal owner accounts from **Create account**, and that action is audited. Admin accounts are not created through the account form. Existing non-demo viewer accounts are migrated to owner on startup; the dedicated `viewer@trustvault.local` remains a read-only demo account.
- Premium iOS-inspired liquid-glass workspace with larger typography, animated ambient lighting, hover/reveal motion, prominent category tiles with per-category counts, document search, library statistics, and a drag-and-drop upload area.
- Owners upload documents, edit metadata, delete their own documents, and grant/revoke named users `read` or `edit` access. Admins may also upload/manage documents they personally own, but admin status does not grant access to other owners’ files.
- A read grant permits metadata view/download only. An edit grant permits metadata edits, but not deletion or sharing. Only the owner can delete or manage grants.
- Admins can view account metadata, recent audit events, and hash-chain verification; admin role alone does not provide document-content access.
- Search/filter by title/filename, owner, category, and date; browse category chips including Finance, Legal, HR, Engineering, Compliance, Customer, Operations, Product, Sales, Security, Marketing, Research, General and Other.
- Dedicated **Manage access** page at `/documents/<id>/share` with current grants, permission updates, revocation, and audited grant changes.
- File validation for PDF, TXT, CSV, PNG, JPG/JPEG and DOCX, with a 5 MB limit.
- Audit events for login success/failure, views, downloads, uploads, edits, deletions, permission changes, and denied document actions.
- Automated tests for anonymous access, IDOR, grant/revocation, read-vs-edit least privilege, forged roles, open redirects, rate limiting, CSRF, response headers, file validation, pagination/shared-view behavior, and audit event/head tampering.

## Stack and storage

- Python 3.12, Flask, Flask-Login, Flask-WTF, Flask-Limiter, Flask-Migrate, SQLAlchemy.
- SQLite for local development and tests; PostgreSQL for Render deployment.
- Document bytes are stored in the database (BLOB/BYTEA), not a public folder or ephemeral service filesystem. Upload limit is 5 MB.
- Production server: Gunicorn.

## Local setup (clean clone)

Requirements: Python 3.12+ and Git.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set a long random SECRET_KEY plus unique demo passwords.
flask --app app db upgrade
python init_db.py
python app.py
```

Open `http://127.0.0.1:5000`.

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
cp .env.example .env
# Edit .env and set a long random SECRET_KEY plus unique demo passwords.
flask --app app db upgrade
python init_db.py
python app.py
```

The app reads environment variables automatically; it does not parse `.env` files itself. If you use `.env`, export its variables in your shell or install a dotenv loader locally. On PowerShell, for example:

```powershell
Get-Content .env | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object { $name,$value = $_ -split '=',2; Set-Item -Path "Env:$name" -Value $value }
```

For the simplest local run, the app has development-only fallback values, but set your own secrets before exposing it on a network. `COOKIE_SECURE=false` is needed for plain local HTTP; use `true` on HTTPS hosting.

## Local demo accounts

These are local demo defaults only; configure `SEED_ADMIN_PASSWORD`, `SEED_OWNER_PASSWORD`, and `SEED_VIEWER_PASSWORD` before deploying. They are not suitable for real data.

| Role | Email | Default local password |
|---|---|---|
| Admin | `admin@trustvault.local` | `ChangeThisAdmin!2026` |
| Document owner | `owner@trustvault.local` | `ChangeThisOwner!2026` |
| Viewer | `viewer@trustvault.local` | `ChangeThisViewer!2026` |

Demo users are seeded by the explicit `python init_db.py` initialization command (and the Render start command runs this once before Gunicorn workers start), not inside each web worker. In local development, the default demo passwords below are available for convenience. In production, startup fails unless `SECRET_KEY` is at least 32 characters and all three `SEED_*_PASSWORD` variables are present and at least 12 characters; configure unique strong values in Render. If a demo account exists with a different password, the app rotates it to the configured secret. New public sign-ups receive the `owner` role, so after signing in they can upload and manage their own documents. Registration itself does not sign them in automatically. This does not grant access to other users’ documents. Existing registered accounts created under the old viewer-only flow are upgraded to `owner` when the app starts (except the dedicated `viewer@trustvault.local` demo account), with a migration audit event. To test read-only access, use the dedicated demo viewer account. Changing the seed environment password does not reset an existing database user's password; for a clean local reset, stop the app and delete `instance/trustvault.db` (the usual Flask-SQLAlchemy location for a relative SQLite URI), then restart.

## Database migrations

Flask-Migrate/Alembic is configured under `migrations/`. The baseline revision creates any missing tables without replacing existing tables. Apply migrations before starting the app:

```bash
flask --app app db upgrade
python init_db.py
```

For future model/schema changes, create and review an explicit revision with `flask --app app db migrate -m "describe schema change"`, inspect the generated migration carefully, and apply it with `flask --app app db upgrade`. The baseline downgrade is intentionally disabled to avoid accidental deletion of user documents and audit history. Back up the database before applying any schema changes.

## Rate limiting and browser protections

- Login POST requests are limited to 10 per minute per client address.
- Registration POST requests are limited to 5 per hour per client address.
- Responses include common security headers, a same-origin-script Content Security Policy, HSTS when secure cookies are enabled, and `Cache-Control: no-store` for dynamic pages. Authenticated sessions use a configured eight-hour default lifetime and do not refresh that lifetime on every request.
- The default rate-limit backend is in-memory for local/single-instance use. Configure `RATELIMIT_STORAGE_URI` to a shared Redis-compatible backend before running multiple instances/workers that must share counters. Render's single Gunicorn worker is configured intentionally for the default in-memory backend.

## Run tests

```bash
python -m pytest -q
```

The test suite uses a temporary SQLite database and disables CSRF only inside test configuration. CSRF protection remains enabled in normal app configuration.

## Render deployment

1. Push the repository to your own GitHub repository. Keep it private while developing if required by the challenge rules; make it public at the allowed submission time.
2. In Render, create a Blueprint from the repository using `render.yaml`, or create a PostgreSQL database and Python web service manually.
3. Use the **internal** PostgreSQL connection string for `DATABASE_URL` on Render. The app normalizes Render's `postgres://` format.
4. Set all of these secrets in the Render web-service environment: `SECRET_KEY` (a long random value), `SEED_ADMIN_PASSWORD`, `SEED_OWNER_PASSWORD`, and `SEED_VIEWER_PASSWORD`. Use unique strong values and keep them out of Git. `COOKIE_SECURE=true` should be set for HTTPS.
5. Build command: `pip install -r requirements.txt`
6. Start command: `flask --app app db upgrade && python init_db.py && gunicorn app:app --workers 1 --threads 4 --timeout 60`
7. Health check path: `/health`.
8. Wait for the service to become healthy. Open the URL in an incognito/private window and test each role. Do not submit the URL until it works for a stranger.

Render free-plan availability and database retention policies can change. Confirm current plan limits in Render before relying on a free database for long-term persistence. The Blueprint file is a starting configuration and may require plan adjustments in the Render dashboard.

## Security model

The server checks permissions on every document detail, download, edit, delete, grant, and revoke request. Public sign-up creates a normal owner account, ignores any submitted role, and never creates an admin. Existing non-demo viewer accounts are upgraded at startup and that migration is audited. The list query includes only documents owned by the current user or with an explicit grant. Hiding buttons in HTML is only a usability feature, not an authorization control. See `API.md` for route-level access requirements and `THREATS.md` for threat analysis and residual risks.

The audit chain is **tamper-evident, not immutable**. Verification checks event hashes, links, and that the final event hash matches the stored audit head. It can detect many event/head changes, but an attacker with sufficient database privileges could rewrite the entire chain and its head. External append-only/WORM log storage is not implemented. Login and registration rate limits are enabled per client address, but the default in-memory backend is process-local and does not coordinate multiple instances. Configure shared Redis storage for multi-instance deployments. Malware scanning, MFA, password reset, SSO, versions, and recovery are not implemented. Do not describe these as implemented.

## Suggested five-minute demo

1. Register a normal account (or sign in as the seeded owner) and upload a small TXT or PDF file. Public sign-ups can upload and manage their own documents; an admin can only access documents they personally own.
2. Open the document and show its SHA-256 metadata.
3. Grant `read` access to the dedicated read-only demo viewer account.
4. Sign out, sign in as the read-only demo viewer, and download the granted file.
5. As viewer, try the edit/delete URL directly and show the denial.
6. Sign in as owner and revoke the viewer grant; sign back in as viewer and retry the same URL to show access is removed.
7. Sign in as admin and show the audit events and chain verification; show that admin cannot open the document unless explicitly granted.
8. Briefly show the security tests, `THREATS.md`, and `PROMPTS.md`.

## Repository files

- `app.py`, `auth.py`, `documents.py`, `admin.py`: app setup and routes.
- `models.py`, `permissions.py`, `audit.py`: data model, access policy, audit chain.
- `tests/`: automated security and functionality tests.
- `THREATS.md`: threat model, controls, tests, accepted limitations.
- `PROMPTS.md`: AI-assisted development record. Keep it accurate and link entries to real commits as you work.
- `API.md`: route-level authorization documentation.
- `SCHEMA.md`: tables, fields, relationships, and storage decisions.
- `DEMO_SCRIPT.md`: a five-minute recording walkthrough.
- `init_db.py`: database initialization helper.

## Individual work and AI disclosure

This starter was generated with AI assistance. Read and understand every route and permission helper before submitting. Run the tests, investigate failures, document actual mistakes and corrections in `PROMPTS.md`, and make incremental commits with honest messages. Do not fabricate commit links, test results, or completed features.
