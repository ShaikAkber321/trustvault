# TrustVault — API and Authorization Reference

## Overview

TrustVault currently uses server-rendered HTML pages, HTML forms, and cookie-based sessions rather than a public JSON REST API.

* Authentication is managed through Flask-Login.
* Applicable POST forms use Flask-WTF CSRF protection.
* Protected routes require authentication.
* Document authorization is enforced by the server.
* Document permissions are checked against current database state.
* Denied document-access attempts are audited where implemented by the relevant route.
* Inaccessible document IDs return HTTP 404 to reduce disclosure of document existence.
* Dynamic responses use `Cache-Control: no-store`.

This document describes the application's documented routes and their access requirements.

## Route Reference

| Method and path                                 | Purpose                                                           | Required access                                                                                                                          | Audit events                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `GET /health`                                   | Health and database check                                         | Public; reveals limited status information                                                                                               | None                                                                  |
| `GET /login`                                    | Display login form                                                | Public                                                                                                                                   | None                                                                  |
| `POST /login`                                   | Authenticate a user                                               | Public; limited to 10 requests per minute per client address                                                                             | `login_success`, `login_failed`                                       |
| `GET /register`                                 | Display registration form                                         | Public                                                                                                                                   | None                                                                  |
| `POST /register`                                | Register an account                                               | Public; always creates a normal `owner` account, ignores submitted role values, and is limited to 5 requests per hour per client address | `user_registered`                                                     |
| `POST /logout`                                  | End the authenticated session                                     | Authenticated                                                                                                                            | `logout`                                                              |
| `GET /`                                         | Search and browse visible documents                               | Authenticated; only owned or explicitly shared documents are visible                                                                     | No general listing event documented                                   |
| `GET /?scope=shared`                            | View documents shared with the current user                       | Authenticated; includes explicitly granted documents not owned by the current user                                                       | No general listing event documented                                   |
| `GET /documents/upload`                         | Display upload form                                               | Authenticated owner or admin                                                                                                             | None                                                                  |
| `POST /documents/upload`                        | Upload a document                                                 | Authenticated owner or admin; the uploader becomes the document owner                                                                    | `document_uploaded`, `denied_upload`                                  |
| `GET /documents/<id>/share`                     | Display document access-management page                           | Owner of the specified document                                                                                                          | `denied_manage_access` on denial                                      |
| `GET /documents/<id>`                           | View document metadata                                            | Document owner or user with an explicit `read` or `edit` grant                                                                           | `document_viewed`, `denied_read`                                      |
| `GET /documents/<id>/download`                  | Download document bytes                                           | Document owner or user with an explicit `read` or `edit` grant                                                                           | `document_downloaded`, `denied_download`                              |
| `GET /documents/<id>/edit`                      | Display metadata-edit form                                        | Document owner or user with an explicit `edit` grant                                                                                     | Route-specific behavior should be verified                            |
| `POST /documents/<id>/edit`                     | Update document metadata                                          | Document owner or user with an explicit `edit` grant                                                                                     | `document_changed`, `denied_edit`                                     |
| `POST /documents/<id>/delete`                   | Delete a document and its grants                                  | Document owner only                                                                                                                      | `document_deleted`, `denied_delete`                                   |
| `POST /documents/<id>/grants`                   | Grant or change a user's read/edit permission                     | Document owner only                                                                                                                      | `permission_granted`, `permission_changed`, `denied_grant_permission` |
| `POST /documents/<id>/grants/<grant_id>/revoke` | Revoke a user's access                                            | Owner of the specified document                                                                                                          | `permission_revoked`, `denied_revoke_permission`                      |
| `GET /admin/activity`                           | View account metadata, audit events, and audit-chain verification | Admin role only; admin role does not grant document-content access                                                                       | `denied_admin_view` for non-admin users                               |
| `GET /admin/users/new`                          | Display account-provisioning form                                 | Admin role only                                                                                                                          | Route-specific behavior should be verified                            |
| `POST /admin/users/new`                         | Create a normal owner account                                     | Admin role only; cannot create an admin account through this form                                                                        | `admin_user_created`, `denied_admin_view` for non-admin users         |

**Note:** Verify route-specific audit behavior against the implementation before treating this table as a complete event inventory. In particular, displaying a form and submitting a form may have different audit behavior.

## Authentication and Sessions

### Public Routes

The following routes are intended to be accessible without an authenticated session:

* `GET /login`
* `POST /login`
* `GET /register`
* `POST /register`
* `GET /health`
* Static assets served by the application

Other private routes require authentication.

### Registration

Public registration creates a normal owner account. The application must not trust a role value supplied by the registration form.

Registration does not automatically authenticate the newly created account. The user must sign in separately.

### Logout

Logout is performed using a POST request. Applicable CSRF protection must be satisfied.

## Document Authorization

### Ownership

A document owner can:

* View and download their own documents.
* Upload documents.
* Edit their own document metadata.
* Delete their own documents.
* Grant and revoke named users' permissions.

### Read Permission

A user with an explicit `read` grant can view and download the corresponding document.

A read grant does not allow the user to edit metadata, delete the document, or manage its sharing permissions.

### Edit Permission

A user with an explicit `edit` grant can view and download the document and edit permitted metadata.

An edit grant does not grant permission to delete the document or manage its sharing permissions.

### Administrative Access

Administrators can access administrative account information and audit activity.

The admin role does not automatically grant access to other users' document contents. An administrator can manage documents they personally own, subject to the same applicable document-authorization rules.

### Revocation

When a document owner revokes a grant, subsequent protected requests must use the current permission state. Revoked access must not remain available through a reusable public download URL.

## Upload Validation

The application documents the following accepted upload types:

* PDF
* TXT
* CSV
* PNG
* JPG/JPEG
* DOCX

The configured upload-size limit is 5 MB.

The server applies upload validation, including applicable file-type or structural checks. These controls do not guarantee that every accepted file is free of malware.

## Audit Trail

The documented audit events include:

* Successful and failed login attempts.
* User registration.
* Document uploads.
* Document views and downloads.
* Document metadata changes.
* Document deletions.
* Permission grants, changes, and revocations.
* Denied document-access attempts.
* Administrative activity.

The audit chain links events using hashes and previous-hash values. Verification checks event hashes, chain links, and the stored terminal hash.

The audit chain is **tamper-evident, not immutable**. An attacker with sufficient database privileges could potentially rewrite the chain and its stored head.

Audit events are retained according to the application's implementation and database lifecycle.

## HTTP Status and Error Handling

The documented authorization behavior includes:

* **HTTP 404:** Used for inaccessible document IDs to reduce disclosure of whether a document exists.
* **HTTP 403:** May be used for access denials where the route does not intentionally return 404.
* **HTTP 400:** May be used for invalid form submissions or invalid input, depending on the route.
* **HTTP 401 or login redirect:** Authentication behavior depends on the route and Flask-Login configuration.

The exact response status and body should be verified against each route's implementation and tests. This document does not define a separate JSON error format because the application primarily uses server-rendered HTML.

## CSRF and Browser Security

Applicable POST forms use Flask-WTF CSRF protection.

The application also configures security response headers, including Content Security Policy, `X-Frame-Options`, `X-Content-Type-Options`, Referrer Policy, and Permissions Policy.

HSTS is enabled when secure-cookie configuration is enabled. Dynamic responses use `Cache-Control: no-store`.

Login and registration requests are rate-limited per client address. The default in-memory rate-limit backend is process-local; multi-instance deployments should use a shared Redis-compatible backend.

## Related Documentation

* `README.md` — installation, configuration, testing, and deployment.
* `THREATS.md` — threats, controls, accepted limitations, and verification checklist.
* `SCHEMA.md` — database schema and storage decisions.
* `PROMPTS.md` — AI-assisted development record.
* `DEMO_SCRIPT.md` — demonstration walkthrough.
