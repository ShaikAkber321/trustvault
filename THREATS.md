# TrustVault Threat Model

**Status:** initial threat model; update it as tests and deployment checks uncover more. Scope is this application and its own deployment only.

## Assets and security goals
- Confidentiality and integrity of document bytes and metadata.
- Correct per-document grants and immediate revocation.
- Audit records that reveal successful and refused access attempts and make tampering detectable.
- Login sessions, passwords, and account-role assignments.

## Trust boundaries
- Browser to Flask application over HTTPS in production.
- Flask application to PostgreSQL/SQLite.
- User-controlled filenames, form fields, search filters, and uploaded bytes.
- Admin audit view versus document-content access. An admin role does **not** implicitly grant access to document bytes.

## Roles and authorization rules
- **admin:** can inspect account metadata and audit events; does not automatically read, edit, download, grant access to, or delete document content.
- **owner:** can upload, read, edit metadata, delete their own documents, and grant/revoke named-user read/edit permissions. **admin:** can manage accounts/audit activity and can upload/manage documents the admin personally owns; admin role alone never grants access to other users’ documents.
- **viewer (read-only account):** can read/download documents with a `read` or `edit` grant. A user with an `edit` grant can edit metadata, but cannot delete or share the document. Role alone never grants access to a document. Public sign-up now creates a normal `owner` account so each person can upload and manage their own documents.
- All document operations re-check the current database grant. No long-lived signed file URLs are issued. Revocation therefore applies to the next request.

## Threats, controls and tests

| Threat | Control | Verification |
|---|---|---|
| Unauthenticated request reaches document routes | Flask-Login on protected routes | `test_unauthenticated_cannot_view_documents` |
| Guessing another document's integer ID (IDOR) | Every detail/download/edit/delete/grant route checks ownership/grant on the server; inaccessible resources return 404 | `test_user_cannot_read_or_download_another_users_document`, `test_read_grant_cannot_edit_or_delete` |
| Read grant is escalated to edit/delete/share | Separate `can_edit` and owner-only `can_delete` checks; only owner can manage grants | `test_read_grant_cannot_edit_or_delete` |
| Access remains after revocation | Grant is deleted in DB; authorization checks DB on every request | `test_grant_then_revoke_takes_effect_immediately` |
| Admin role becomes a universal document bypass | Admin content access is not implicit | `test_admin_role_does_not_implicitly_grant_document_content_access` |
| Spoofed extension / malformed file | Extension allowlist, size limit, signature or structural checks for supported types | `test_invalid_file_signature_is_rejected` |
| Audit rows, ordering, or head pointer are modified | Hash-linked events; verification checks event hashes, previous links, and terminal hash against `AuditHead.last_hash` | `test_audit_chain_detects_tampering`, `test_audit_chain_detects_head_row_tampering` |
| Failed access attempt is invisible | Denied read/download/edit/delete/share attempts are recorded before returning 404/403 | IDOR tests inspect `denied_read` and `denied_download` events |
| Cross-site request forgery on form actions | Flask-WTF CSRF tokens on POST forms | `test_csrf_rejects_login_post_without_token`; CSRF is enabled by default |
| Open redirect after login, including scheme-relative/backslash variants | `next` is accepted only as a local absolute path with no scheme, host, or backslash; malformed URL parsing is rejected | `test_login_next_parameter_cannot_redirect_off_site` |
| Password disclosure in source | Password hashes stored; seed passwords injected through environment variables in deployment | Inspect DB; ensure Render secrets are set and not committed |
| SQL injection through search fields | SQLAlchemy parameterized query expressions; no raw user-built SQL | Search with quotes and SQL-looking strings; verify normal results/no server error |
| Audit chain is tampered with by a database administrator | Hash chain detects many changes but does not defeat an attacker who can rewrite the entire database and chain head | **Accepted limitation:** production-grade evidence should also stream events to external append-only/WORM storage and restrict DB credentials |
| Stored file malware or parser exploit | File type and size checks; files are downloaded as attachments, not rendered inline | **Accepted limitation:** no antivirus scanning or content disarm/reconstruction in this version |
| Brute-force login and registration spam | Login POST is limited to 10/minute and registration POST to 5/hour per client address; generic failures and audit events remain | `test_login_is_rate_limited`; residual risk: in-memory counters are process-local; configure shared Redis for multi-instance deployments |
| Demo accounts are publicly known | Separate environment-configurable passwords | **Required before deployment:** set strong unique `SEED_*_PASSWORD` values in Render; README demo credentials are for local evaluation only |
| Browser clickjacking/content sniffing/cached private pages | CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy and no-store on dynamic responses | `test_security_headers_are_set`; inspect response headers on the live deployment |
| Sensitive file bytes stored in database | Access is through protected Flask routes, not public object URLs | **Accepted limitation:** database/storage encryption-at-rest depends on hosting provider; application-level encryption is not implemented |

## Residual risks and deliberately omitted features
- Public account registration is implemented and creates a normal document-owning account; registration does not automatically authenticate the new account. Password reset, MFA and SSO are not implemented.
- No virus scanning, document version history, retention automation, or recovery bin.
- The audit chain is tamper-evident, not cryptographically immutable against a fully privileged database operator. External log anchoring is the next improvement.
- SQLite is for local development/tests. Use Render PostgreSQL for deployment. The file bytes are stored as database BLOB/BYTEA values to avoid ephemeral local filesystem storage on a free web service; the 5 MB limit keeps this practical for the challenge.
- No external/guest users, group grants, or folder inheritance. Permissions are direct per-document grants only.

## Deployment verification checklist
1. Set a random `SECRET_KEY`, unique `SEED_ADMIN_PASSWORD`, `SEED_OWNER_PASSWORD`, and `SEED_VIEWER_PASSWORD`; set `COOKIE_SECURE=true`.
2. Use Render's internal PostgreSQL connection string; do not use SQLite for a deployed instance.
3. Open the live URL in a private/incognito window and sign in with each role.
4. Create a document as owner; confirm an ungranted viewer cannot view/download it by guessing its URL.
5. Grant read access, verify download, revoke, and immediately retry the same URL.
6. Confirm a read-only grantee cannot edit, delete, or grant access.
7. Confirm admin can inspect the audit page but cannot read a document without a grant.
8. Check the audit chain status after upload, download, denied access, grant, and revoke.


## Additional checks added during UI/access workflow revision

- **Upload is not discoverable for an admin:** admins may upload a document they own, but cannot read another owner's document by virtue of role. Regression test: `test_admin_can_upload_only_a_document_they_own`.
- **Share/manage-access URL guessing:** `GET /documents/<id>/share` requires document ownership and returns the same not-found response for a non-owner. Regression test: `test_manage_access_page_is_owner_only`.
- **Category filtering:** category chips only alter the search query; they do not broaden the server-side visible-document query. Document visibility is always restricted to owned documents or explicit grants.


## Registration policy update (2026-10-24)

- Public registration creates `owner`, which means the person may upload, edit, delete, and share documents they own. It does **not** grant access to documents owned by anyone else.
- The role supplied in a registration form is ignored. The public endpoint never creates `admin`.
- On startup, existing `viewer` accounts are migrated to `owner`, except the dedicated `viewer@trustvault.local` demo account used for negative-access demonstrations. Each migration is recorded in the audit trail. Review this exception if changing demo account conventions.
- Read/edit sharing remains per-document and server-enforced. An account can be an owner of its own documents while holding read/edit grants on other users’ documents.


## Authentication entry-point review (2026-10-24)
- The workspace route (`/`) and every document route must require an authenticated session; anonymous visitors should be redirected to `/login`. Public routes are limited to login, registration, static assets, and the health check.
- Registration creates an `owner` account but does not automatically sign the person in; successful registration redirects to the login form. This makes the login/signup screen the initial experience for a new visitor.
- The session cookie name was versioned to invalidate old cookies from the previous build that may make the new app appear to skip login.
- Production must use a random `SECRET_KEY` of at least 32 characters and unique `SEED_*_PASSWORD` values of at least 12 characters; startup fails if these are missing, and existing demo-account passwords are rotated to configured values if they differ.
- Automated tests added for anonymous access to the workspace, upload, document, download, share, and admin routes, plus forged-role registration. Run these tests locally before submission and record the actual result.


## Additional hardening review (2026-10-24)

- Login and registration POSTs now have per-client rate limits. The default `memory://` store is process-local; use a shared Redis-compatible `RATELIMIT_STORAGE_URI` if running multiple instances. The included Render configuration uses one Gunicorn worker to avoid splitting counters between workers by default. A single IP may still represent multiple users behind a NAT, and distributed attackers can evade per-address limits.
- Audit verification now checks the stored terminal head hash as well as each event hash and previous-hash link. This remains tamper-evident rather than immutable.
- Security response headers are added centrally, including CSP, `X-Frame-Options`, `X-Content-Type-Options`, referrer and permissions policies, HSTS when secure cookies are enabled, and no-store for dynamic responses. JavaScript was moved to same-origin static files so the CSP does not need `unsafe-inline` for scripts; inline styles remain permitted for CSS effects.
- DOCX uploads are bounded by both compressed upload size and total uncompressed archive size. Files remain served as attachments after an authorization check.
- Startup schema creation/seeding is no longer run in each Gunicorn worker. The Render start command applies the Alembic baseline, runs the one-time initialization/seeding script, and then starts a single worker. Future schema changes need reviewed migrations and database backups.
- Verification status: syntax and archive checks can be performed before packaging, but full runtime tests must be run in an environment where requirements install successfully. Do not claim the suite passes until local output confirms it.
