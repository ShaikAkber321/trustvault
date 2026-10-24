# Route / API authorization reference

TrustVault currently uses server-rendered HTML forms and cookie sessions rather than a public JSON API. All POST forms use Flask-WTF CSRF tokens. `login_required` protects the routes marked authenticated.

| Method + path | Purpose | Required access | Audit event |
|---|---|---|---|
| `GET /health` | Liveness/database check | Public; reveals only status | None |
| `GET, POST /login` | Sign in | Public; POST limited to 10/minute per client address | `login_success` / `login_failed` |
| `GET, POST /register` | Create an account | Public; always creates a normal `owner` account, ignores any submitted role; never creates an admin; POST limited to 5/hour per client address | `user_registered` |
| `POST /logout` | End session | Authenticated | `logout` |
| `GET /` | Search visible documents / `?scope=shared` | Authenticated; query restricted to owned or granted documents; shared scope includes only granted documents not owned by the current user | None (document details are audited on open) |
| `GET, POST /documents/upload` | Upload a document | Authenticated normal owner or admin; every upload is owned by uploader; admin role never grants access to other owners’ files | `document_uploaded`, `denied_upload` |
| `GET /documents/<id>/share` | Manage explicit read/edit grants | Document owner only; admin role alone does not grant access to other owners' files | `denied_manage_access` on denial |
| `GET /documents/<id>` | Read document metadata | Owner or explicit read/edit grant | `document_viewed`, `denied_read` |
| `GET /documents/<id>/download` | Download bytes | Owner or explicit read/edit grant | `document_downloaded`, `denied_download` |
| `GET, POST /documents/<id>/edit` | Edit metadata | Owner or explicit edit grant | `document_changed`, `denied_edit` |
| `POST /documents/<id>/delete` | Delete document and grants | Owner only | `document_deleted`, `denied_delete` |
| `POST /documents/<id>/grants` | Grant/change read or edit access | Owner only | `permission_granted` / `permission_changed`, `denied_grant_permission` |
| `POST /documents/<id>/grants/<grant_id>/revoke` | Revoke access | Owner of that document only | `permission_revoked`, `denied_revoke_permission` |
| `GET /admin/activity` | View account metadata and audit events; verify chain | Admin role only; does not grant document content access | `denied_admin_view` for non-admin |
| `GET, POST /admin/users/new` | Provision a normal owner account | Admin role only; cannot create admins | `admin_user_created`, `denied_admin_view` for non-admin |

Inaccessible document IDs return 404 so an ungranted user cannot easily distinguish a real document from a nonexistent ID. Audit entries for denied attempts are retained. Permission changes are checked against the database on every subsequent request; no reusable public download URL is created.

Responses also receive centrally configured security headers; dynamic responses use `Cache-Control: no-store`. See README for rate-limit storage requirements and migrations.
