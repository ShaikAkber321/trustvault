# TrustVault Database Schema

The SQLAlchemy models in `models.py` are the source of truth for the database schema. The `db.create_all()` operation creates missing tables, and `python init_db.py` provides an explicit database initialization command.

## Tables

### `user`

Stores user accounts and authentication information.

* `id`: Primary key.
* `name`: User's name.
* `email`: Unique email address.
* `role`: `admin`, `owner`, or `viewer`.
* `password_hash`: Werkzeug password hash; plaintext passwords are never stored.
* `active`: Indicates whether the account is active.
* `created_at`: Account creation timestamp.

Public registration creates normal `owner` accounts. The `viewer` role is retained for the dedicated read-only demo/test account and explicitly read-only accounts.

### `document`

Stores document metadata and file contents.

* `id`: Primary key.
* `owner_id`: Foreign key referencing `user.id`.
* `title`: Document title.
* `original_filename`: Original uploaded filename.
* `category`: Document category.
* `description`: Document description.
* `content`: Binary file contents stored in the database.
* `content_type`: File content type.
* `size_bytes`: File size in bytes.
* `sha256`: SHA-256 hash of the document content.
* `created_at`: Creation timestamp.
* `updated_at`: Last-update timestamp.

### `document_grant`

Stores document-specific access permissions.

* `id`: Primary key.
* `document_id`: Foreign key referencing `document.id`, with cascade deletion.
* `user_id`: Foreign key referencing `user.id`.
* `created_by_id`: Foreign key referencing `user.id`.
* `permission`: `read` or `edit`.
* `(document_id, user_id)`: Unique pair, allowing one grant per user for each document.
* `created_at`: Grant creation timestamp.

### `audit_head`

Maintains the current head of the audit hash chain.

* `id`: Singleton row with `id = 1`.
* `last_hash`: Hash of the latest audit event.

On PostgreSQL, the row is locked when appending events to serialize updates to the hash chain.

### `audit_event`

Stores security-relevant activity and audit-chain information.

* `id`: Primary key.
* `event_uuid`: Unique event identifier.
* Actor ID and email.
* Action performed.
* Document ID and target user ID, where applicable.
* JSON-encoded event details.
* Client IP address and user-agent.
* Event timestamp.
* `previous_hash`: Hash linking to the preceding event.
* `event_hash`: Unique hash for the event.

Audit actor and document IDs deliberately have no foreign keys so that audit history can survive the deletion of users or documents.

## Relationships and Security

* One user can own multiple documents.
* A document can have multiple direct access grants, with at most one grant per target user.
* A grant does not make a document public.
* Read, download, edit, and delete operations must enforce the applicable ownership and permission checks.
* Document bytes are not served from a public static directory.
* Audit hashes help detect changes to the audit chain, but the database is not an immutable or write-once audit store.

See `THREATS.md` for the threat model and documented security limitations.

## Schema Migration Policy

Flask-Migrate and Alembic are configured under `migrations/`.

The baseline revision uses SQLAlchemy metadata with `create_all(checkfirst=True)` to create missing current tables while preserving tables from the earlier starter schema. It does not perform column alterations.

Future schema changes must be generated, reviewed, and applied through explicit Alembic revisions. The baseline downgrade is disabled to help prevent accidental destruction of stored document bytes and audit history.
