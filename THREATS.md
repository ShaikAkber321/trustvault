# TrustVault Threat Model

**Status:** Initial threat model with implementation and verification notes. This document covers the TrustVault application and its deployment. Security claims should be supported by code inspection, automated tests, and deployment checks where applicable.

## 1. Assets and Security Goals

The primary assets and security goals are:

* Confidentiality and integrity of document contents and metadata.
* Correct enforcement of per-document permissions and immediate access revocation.
* Audit records of successful and denied access attempts, with tampering detectable through verification.
* Protection of login sessions, password hashes, and account-role assignments.
* Availability and reliability of document management and authentication services.
* Protection of configuration secrets and database credentials.

## 2. Trust Boundaries

TrustVault has the following trust boundaries:

* **Browser to Flask application:** Production traffic should use HTTPS.
* **Flask application to database:** The application accesses document metadata, permissions, document bytes, and audit records.
* **User-controlled input:** Filenames, uploaded bytes, form fields, search filters, and URL parameters must be treated as untrusted.
* **Administrative functions versus document access:** Administrative access to account information and audit events does not automatically grant access to document contents.
* **Application to hosting infrastructure:** Database persistence, encryption at rest, service availability, and network security depend partly on the hosting provider and deployment configuration.

## 3. Roles and Authorization Rules

### Admin

* Can inspect account metadata and audit activity.
* Can manage accounts through the application's administrative functions.
* Can upload and manage documents that the admin personally owns.
* Does not automatically gain permission to read, download, edit, delete, or share another user's documents.

### Owner

* Can upload and organize documents.
* Can read and download documents they own.
* Can edit permitted document metadata and delete their own documents.
* Can grant or revoke named users' read or edit permissions for their documents.
* Cannot access another user's document merely because they have an owner role.

### Viewer and Other Registered Users

* Public registration creates a normal `owner` account so the user can manage their own documents.
* A user with a read grant can read or download the shared document.
* A user with an edit grant can read or download the document and edit permitted metadata.
* An edit grant does not grant permission to delete the document or manage its sharing permissions.
* A user's role alone does not grant access to another user's document.
* The dedicated demo viewer account is used to demonstrate denied access and sharing behavior.

### Authorization Enforcement

* Document access is checked on the server for each protected request.
* The application checks current ownership or document-specific grants rather than relying only on the user interface.
* Revocation removes the grant, so subsequent requests must be denied unless another valid permission exists.
* Public registration must never allow a user to assign themselves the admin role by submitting a modified form.

## 4. Threats, Controls, and Verification

| Threat                                                      | Control or Mitigation                                                                                                                     | Verification                                                                                                 |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Unauthenticated users access protected document routes      | Flask-Login protects private routes.                                                                                                      | `test_unauthenticated_cannot_view_documents` and related private-route tests.                                |
| A user guesses another document's integer ID (IDOR)         | Server-side ownership and grant checks are applied to document operations. Inaccessible resources return an appropriate denial response.  | `test_user_cannot_read_or_download_another_users_document`                                                   |
| A read-only user edits or deletes a document                | Read and edit permissions are checked separately. Deletion and sharing management require ownership.                                      | `test_read_grant_cannot_edit_or_delete`                                                                      |
| Access remains after a grant is revoked                     | Permissions are checked against current database state on subsequent requests.                                                            | `test_grant_then_revoke_takes_effect_immediately`                                                            |
| Admin role becomes a universal document-access bypass       | Administrative privileges do not automatically grant access to other users' document contents.                                            | `test_admin_role_does_not_implicitly_grant_document_content_access`                                          |
| An attacker submits a forged role during registration       | Public registration assigns the permitted role on the server instead of trusting a submitted role value.                                  | `test_forged_admin_registration_rejected`                                                                    |
| Invalid or spoofed uploads bypass basic validation          | Upload extension, size, and supported-file content checks are applied. DOCX files also receive archive-size checks.                       | `test_invalid_file_signature_is_rejected` and related upload tests.                                          |
| Unauthorized attempts are absent from the audit trail       | Denied document-access attempts are recorded before the request is rejected, where implemented by the relevant route.                     | IDOR tests inspect denied-read and denied-download events.                                                   |
| Audit events are modified or removed                        | Events are linked using hashes and previous-hash values. Verification checks event hashes, links, and the stored terminal hash.           | `test_audit_chain_detects_tampering` and `test_audit_chain_detects_head_row_tampering`                       |
| Cross-site request forgery (CSRF)                           | Flask-WTF CSRF protection is enabled for applicable form submissions.                                                                     | `test_csrf_rejects_login_post_without_token`                                                                 |
| Login redirects to an attacker-controlled site              | The login redirect parameter is restricted to acceptable local paths; unsafe URL forms are rejected.                                      | `test_login_next_parameter_cannot_redirect_off_site`                                                         |
| Passwords are exposed in source code                        | Passwords should be stored as hashes. Deployment seed passwords are supplied through environment variables rather than committed secrets. | Review account creation and password-hashing code; check deployment secrets.                                 |
| SQL injection through search filters                        | SQLAlchemy query expressions are used instead of constructing raw SQL from user-controlled input.                                         | Review query construction and test search inputs containing quotes and SQL-like strings.                     |
| Brute-force login attempts                                  | Login POST requests are rate-limited per client address.                                                                                  | `test_login_is_rate_limited`                                                                                 |
| Automated registration spam                                 | Registration POST requests are rate-limited per client address.                                                                           | Review the registration rate-limit configuration and test behavior.                                          |
| Publicly known demo passwords are reused in production      | Production must use strong, unique environment-configured seed passwords.                                                                 | Verify Render environment variables and ensure production credentials are not the documented local defaults. |
| Clickjacking, content sniffing, or caching of private pages | Security response headers and no-store behavior are configured.                                                                           | `test_security_headers_are_set`; inspect response headers on the deployed application.                       |
| Private document bytes are exposed through public file URLs | Document bytes are served through application routes protected by authorization checks rather than public object URLs.                    | Test document download routes with authorized and unauthorized accounts.                                     |

## 5. Accepted Limitations and Residual Risks

### Audit Trail

The audit chain is tamper-evident, not cryptographically immutable against an attacker who can rewrite the entire database and its chain head.

A production deployment requiring stronger audit evidence should send events to independently controlled append-only or WORM storage, restrict database credentials, and consider external anchoring of audit hashes.

### Malicious Files

File extension, size, and content checks reduce the risk of accepting invalid uploads but do not establish that every uploaded file is safe.

This version does not include antivirus scanning or content disarm and reconstruction. A malicious document could still pose a risk to a user who opens it with a vulnerable local application.

### Encryption at Rest

Application-level encryption of stored document bytes is not implemented. Encryption at rest depends on the database and hosting provider's configuration and guarantees.

### Rate Limiting

The default `memory://` rate-limit store is process-local. Counters may reset when the process restarts, and multiple workers or instances may not share counters.

The current Render configuration uses one Gunicorn worker by default. A scaled deployment should use a shared Redis-compatible rate-limit store.

Per-address rate limits can affect multiple legitimate users behind the same NAT and may be bypassed by attackers distributing requests across addresses.

### Authentication Features

The application does not include multi-factor authentication, single sign-on, or a password-reset workflow in this version.

### Document Management

The application does not include document version history, automated retention, a recovery bin, group-based grants, folder permission inheritance, or external guest accounts.

### Hosting and Availability

The free hosting configuration may experience cold starts, resource limits, or service interruptions. Free database availability and retention are governed by the hosting provider's current policies.

A production deployment should use appropriate backups, recovery procedures, monitoring, and hosting capacity.

## 6. File Upload and Storage Security

* The application enforces a maximum upload size configured through `MAX_CONTENT_LENGTH`.
* Supported file types are restricted by the application's upload-validation logic.
* Supported file types receive the applicable signature or structural checks.
* DOCX archive contents are checked against configured size limits to reduce archive-expansion risks.
* Uploaded bytes are stored in the database to avoid dependence on ephemeral local filesystems in the deployed environment.
* Document downloads pass through protected application routes.
* Files are served as attachments rather than intentionally rendered inline.
* File validation does not replace antivirus scanning or a comprehensive malware-analysis process.

The configured upload limit is 5 MB. Any change to the supported file types or size limits should be accompanied by appropriate tests.

## 7. Account Registration and Provisioning

* Public registration creates an owner account.
* Public registration must not allow users to select or obtain the admin role by changing submitted form fields.
* Registration does not automatically authenticate the new account; successful registration redirects the user to the login page.
* Administrative account provisioning is restricted to authorized administrative functionality.
* Existing account-role migration behavior should be reviewed whenever the account model or demo-account conventions change.
* The dedicated demo viewer account is an exception to the migration of legacy viewer accounts to owner accounts.
* Production seed passwords must be configured through secure environment variables and must not reuse local demonstration credentials.

## 8. Automated Test Coverage

The local test run previously reported **26 passing tests**.

The reported test coverage includes:

* Registration and authentication behavior.
* Protection of private routes against anonymous access.
* Document upload, search, editing, downloading, and deletion.
* Document ownership and per-document permission enforcement.
* Granting and revoking document access.
* Restrictions on read-only and edit-only grants.
* Administrative access boundaries.
* Upload validation.
* Audit-chain and audit-head tampering detection.
* Denied-access audit events.
* CSRF protection.
* Login rate limiting.
* Security response headers.
* Protection against unsafe post-login redirects.

The test count and results should be rechecked after any code or test changes.

Run the test suite from the project directory using:

```powershell
python -m pytest -v
```

Do not describe a test as passing unless the actual test output confirms it.

## 9. Deployment Verification Checklist

Complete these checks against the actual deployed application before submission.

### Configuration

* [ ] Set a strong, random production `SECRET_KEY`.
* [ ] Set unique, strong `SEED_ADMIN_PASSWORD`, `SEED_OWNER_PASSWORD`, and `SEED_VIEWER_PASSWORD` values.
* [ ] Confirm production cookies use `COOKIE_SECURE=true`.
* [ ] Confirm the deployed service uses the intended PostgreSQL database connection.
* [ ] Confirm no real credentials, private keys, or `.env` files are committed to Git.
* [ ] Confirm the deployment starts successfully and the health endpoint responds.

### Authentication and Authorization

* [ ] Open the live URL in a private/incognito browser window and verify that private pages require authentication.
* [ ] Register a new account and verify that registration does not automatically sign the user in.
* [ ] Sign in with the appropriate test accounts.
* [ ] Create a document as an owner.
* [ ] Verify that an ungranted user cannot view or download that document, including by guessing its URL.
* [ ] Grant read access and verify that the recipient can read or download the document.
* [ ] Revoke the grant and retry the same request; verify that access is denied.
* [ ] Verify that a read-only grantee cannot edit, delete, or share the document.
* [ ] Verify that an edit grantee can perform permitted metadata edits but cannot delete or share the document.
* [ ] Verify that an admin can inspect administrative audit information but cannot read another user's document without permission.

### Audit and Response Headers

* [ ] Confirm that upload, download, permission changes, and relevant denied attempts create the expected audit events.
* [ ] Check the audit-chain verification result after performing representative actions.
* [ ] Inspect the live response headers and verify the expected security headers are present.
* [ ] Confirm that private responses use the intended cache-control policy.

Only mark a checklist item complete after observing the result.

## 10. Final Security Statement

TrustVault implements authentication, server-side document authorization, named-user permissions, revocation checks, upload validation, audit-chain verification, and several web-security protections.

These controls address the threats identified in this document, but they do not guarantee that the application is free of vulnerabilities. Remaining limitations include the absence of antivirus scanning, application-level encryption at rest, externally immutable audit storage, and several advanced authentication and recovery features.

The security posture should be reassessed whenever authorization logic, upload handling, account provisioning, audit behavior, database configuration, or deployment architecture changes.
