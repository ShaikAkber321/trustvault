# TrustVault — Secure Document Sharing with an Audit Trail

TrustVault is a document-sharing application built for a hiring challenge. It provides named per-document permissions, server-side access checks, document search, validated uploads, and an audit trail with a tamper-evident hash chain.

> **Challenge/demo software, not a production document-management service.** Review `THREATS.md` for known limitations. Do not upload real confidential data. Configure strong, unique secrets before deployment.

## Features

### Authentication and Roles

* Session-based authentication with login and public registration.
* Anonymous visitors must sign in before accessing the workspace or document routes.
* Public registration creates a normal document-owning account and does not automatically sign the user in.
* The public registration form cannot be used to assign the admin role.
* Admins can provision normal owner accounts through the administrative interface.
* The application supports `admin`, `owner`, and `viewer` roles.
* Existing non-demo viewer accounts are migrated to owner accounts on startup, except for the dedicated `viewer@trustvault.local` demonstration account.

### Document Management

* Upload supported documents with a configured maximum size of 5 MB.
* Organize documents by category.
* Search and filter by title, filename, owner, category, and date.
* View document metadata and SHA-256 information where provided by the application.
* Edit metadata and delete documents according to the authorization rules.
* Store document bytes in the database rather than a public folder or ephemeral application filesystem.

### Document Sharing and Permissions

* Owners can grant or revoke named users' `read` and `edit` permissions.
* A read grant permits viewing and downloading a shared document.
* An edit grant permits viewing, downloading, and permitted metadata edits.
* An edit grant does not permit deletion or sharing-management operations.
* Only the document owner can delete the document or manage its grants.
* Admin status does not automatically grant access to another user's document contents.
* Authorization is enforced on the server for protected document operations.

### Audit Trail and Security

* Record supported events, including login success and failure, document views, downloads, uploads, edits, deletions, permission changes, and denied document actions.
* Link audit events using hashes and previous-hash values.
* Verify event hashes, chain links, and the stored audit head.
* Apply upload validation and size limits.
* Enable CSRF protection for applicable form submissions.
* Apply rate limits to login and registration POST requests.
* Configure security response headers and no-store behavior for dynamic pages.

### User Interface

* Liquid-glass-inspired workspace design.
* Category navigation and category counts.
* Document search and library statistics.
* Drag-and-drop upload interface.
* Dedicated **Manage access** page for document owners.

## Technology Stack

* **Language:** Python 3.12
* **Web framework:** Flask
* **Authentication:** Flask-Login
* **Forms and CSRF:** Flask-WTF
* **Rate limiting:** Flask-Limiter
* **Database ORM:** SQLAlchemy / Flask-SQLAlchemy
* **Migrations:** Flask-Migrate / Alembic
* **Local database:** SQLite
* **Deployment database:** PostgreSQL
* **Production server:** Gunicorn
* **Testing:** pytest

## Supported Upload Types

The application is configured to accept:

* PDF
* TXT
* CSV
* PNG
* JPG/JPEG
* DOCX

The maximum upload size is 5 MB. File-type and structural checks reduce the risk of invalid uploads but do not replace antivirus scanning.

## Local Setup

### Requirements

* Python 3.12 or a compatible Python version supported by the dependencies.
* Git.
* PowerShell on Windows, or a shell on macOS/Linux.

### Windows PowerShell

Open PowerShell in the project directory.

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Upgrade pip and install the dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and configure a unique, sufficiently long `SECRET_KEY` and unique local demo passwords.

**Important:** The application does not automatically load `.env` files. In PowerShell, load the variables with:

```powershell
Get-Content .env |
    Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } |
    ForEach-Object {
        $name, $value = $_ -split '=', 2
        Set-Item -Path "Env:$name" -Value $value
    }
```

Apply database migrations and initialize the demo accounts:

```powershell
flask --app app db upgrade
python init_db.py
```

Start the application:

```powershell
python app.py
```

Open:

http://127.0.0.1:5000

For plain local HTTP, configure `COOKIE_SECURE=false`. Use `COOKIE_SECURE=true` when deploying behind HTTPS.

### macOS/Linux

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create and edit the environment file:

```bash
cp .env.example .env
```

Export the environment variables into the current shell. For example, if you use Bash:

```bash
set -a
source .env
set +a
```

Apply migrations, initialize the database, and start the application:

```bash
flask --app app db upgrade
python init_db.py
python app.py
```

Open http://127.0.0.1:5000.

## Local Demo Accounts

The following are example local development credentials. They are not suitable for production.

| Role           | Email                     | Example local password  |
| -------------- | ------------------------- | ----------------------- |
| Admin          | `admin@trustvault.local`  | `ChangeThisAdmin!2026`  |
| Document owner | `owner@trustvault.local`  | `ChangeThisOwner!2026`  |
| Viewer         | `viewer@trustvault.local` | `ChangeThisViewer!2026` |

These accounts are created by running:

```powershell
python init_db.py
```

The Render startup command also initializes demo accounts before starting Gunicorn.

### Credential Safety

* Do not use the example passwords in a production deployment.
* Configure unique values for `SEED_ADMIN_PASSWORD`, `SEED_OWNER_PASSWORD`, and `SEED_VIEWER_PASSWORD`.
* Configure a strong production `SECRET_KEY` of at least 32 characters.
* Production seed passwords must meet the application's configured minimum length.
* Never commit real credentials or the `.env` file to Git.
* Public registration creates an owner account but does not automatically sign the user in.
* The dedicated demo viewer account is intended for demonstrating read-only access and denied operations.

If a local database already exists, changing a seed environment variable may not reset an existing user's password in every situation. For a clean local reset, stop the application and delete the local SQLite database only if you no longer need its data. Then rerun the initialization process.

## Database Migrations

TrustVault uses Flask-Migrate/Alembic for database migrations.

Apply existing migrations:

```bash
flask --app app db upgrade
```

Initialize demo accounts:

```bash
python init_db.py
```

For future model changes, generate and review a migration:

```bash
flask --app app db migrate -m "describe schema change"
flask --app app db upgrade
```

Review generated migrations before applying them. Back up the database before schema changes. The baseline migration's downgrade behavior is intentionally restricted to avoid accidental deletion of existing documents and audit history.

## Security Configuration

### Rate Limiting

The application applies the following configured limits:

* Login POST requests: 10 requests per minute per client address.
* Registration POST requests: 5 requests per hour per client address.

The default `memory://` rate-limit backend is intended for local or single-instance use. Its counters are process-local and may reset on restart.

For a multi-instance deployment, configure a shared Redis-compatible backend using `RATELIMIT_STORAGE_URI`.

### Browser Protections

The application configures security response headers, including Content Security Policy, `X-Frame-Options`, `X-Content-Type-Options`, Referrer Policy, and Permissions Policy. HSTS is enabled when secure-cookie configuration is enabled, and dynamic responses use `Cache-Control: no-store`.

These controls reduce specific risks but do not guarantee that the application is free of vulnerabilities.

## Run Automated Tests

Activate your virtual environment, then run:

```bash
python -m pytest -v
```

The test suite uses a temporary SQLite database and disables CSRF only within its test configuration. CSRF protection remains enabled in the normal application configuration.

The tests cover areas including:

* Authentication and private-route protection.
* Document ownership and access control.
* Read/edit permission separation.
* Granting and revoking access.
* Unauthorized document access and downloads.
* Registration role restrictions.
* File validation.
* Audit-chain and audit-head tampering.
* CSRF protection.
* Rate limiting.
* Security response headers.
* Open-redirect protection.

The test result must be taken from the actual test output after the latest code changes.

## Render Deployment

TrustVault can be deployed to Render using the included `render.yaml` as a starting point.

1. Push the repository to GitHub. Follow the challenge's rules about when the repository may become public.

2. Create a Render Blueprint from the repository or configure the PostgreSQL database and web service manually.

3. Configure `DATABASE_URL` using the Render PostgreSQL internal connection string.

4. Configure the following environment variables in the web service:

   * `SECRET_KEY`
   * `SEED_ADMIN_PASSWORD`
   * `SEED_OWNER_PASSWORD`
   * `SEED_VIEWER_PASSWORD`
   * `COOKIE_SECURE=true`

5. Use this build command:

   ```bash
   pip install -r requirements.txt
   ```

6. Use this start command:

   ```bash
   flask --app app db upgrade && python init_db.py && gunicorn app:app --workers 1 --threads 4 --timeout 60
   ```

7. Set the health-check path to `/health`.

8. Wait for deployment to complete and check the service logs.

9. Open the deployed URL in a private/incognito browser window and verify authentication, document permissions, revocation, audit events, and the health endpoint.

Do not submit the live URL until you have verified that the deployed application works for a new visitor.

Render's free-plan availability, service behavior, and database-retention policies may change. Confirm the current limits before relying on a free database for long-term persistence.

## Security Model

The server checks permissions for protected document operations, including document details, downloads, edits, deletions, and permission changes.

The document catalogue is restricted to documents owned by the current user or explicitly shared with them. Hiding buttons in the interface is a usability feature, not a security boundary.

Public registration assigns the owner role on the server and does not permit users to assign themselves the admin role.

See:

* `API.md` for route-level authorization documentation.
* `SCHEMA.md` for database tables and relationships.
* `THREATS.md` for identified threats, implemented controls, and accepted limitations.

### Known Security Limitations

The audit chain is **tamper-evident, not immutable**. An attacker with sufficient database privileges could potentially rewrite the event chain and its stored head.

This version does not include:

* Antivirus scanning.
* Application-level encryption at rest.
* External append-only/WORM audit storage.
* Multi-factor authentication.
* Password-reset functionality.
* Single sign-on.
* Document version history.
* A recovery bin.
* Shared Redis rate-limit storage in the default deployment configuration.

Do not describe these features as implemented.

## Suggested Five-Minute Demo

Use test documents and demonstration accounts rather than real confidential data.

1. Register a normal account or sign in as the seeded owner.
2. Upload a small TXT or PDF file.
3. Open the document and show its metadata, including SHA-256 information if displayed.
4. Grant `read` access to the dedicated demo viewer account.
5. Sign out, sign in as the viewer, and download the shared document.
6. Attempt an edit or delete operation as the viewer and demonstrate that access is denied.
7. Sign in as the owner and revoke the viewer's grant.
8. Sign in as the viewer again and retry the protected operation to demonstrate that access has been revoked.
9. Sign in as admin and show the audit events and chain-verification interface.
10. Demonstrate that admin cannot access another user's document without a valid grant.
11. Briefly show the automated tests, `THREATS.md`, and `PROMPTS.md`.

Record the demo using the actual behavior of the deployed application. Do not claim an operation succeeded unless you observed the result.

## Repository Structure

| File or directory  | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `app.py`           | Application setup and entry point                |
| `auth.py`          | Authentication and account registration          |
| `documents.py`     | Document routes and management                   |
| `admin.py`         | Administrative functionality                     |
| `models.py`        | Database models                                  |
| `permissions.py`   | Document authorization rules                     |
| `audit.py`         | Audit-event recording and verification           |
| `tests/`           | Automated security and functionality tests       |
| `THREATS.md`       | Threat model, mitigations, and residual risks    |
| `PROMPTS.md`       | AI-assisted development record                   |
| `API.md`           | API routes and authorization requirements        |
| `SCHEMA.md`        | Database schema and storage decisions            |
| `DEMO_SCRIPT.md`   | Demo walkthrough                                 |
| `init_db.py`       | Database initialization and demo-account seeding |
| `migrations/`      | Database migration history                       |
| `requirements.txt` | Python dependencies                              |
| `render.yaml`      | Render deployment configuration                  |

## Individual Work and AI Disclosure

This project was developed with AI assistance. Before submission, review and understand the application routes, permission helpers, database models, audit implementation, and tests.

Run the tests, investigate failures, document genuine mistakes and corrections in `PROMPTS.md`, and maintain an honest Git history. Do not fabricate commit links, test results, or completed features.
