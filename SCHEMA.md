# TrustVault database schema

The SQLAlchemy models in `models.py` are the source of truth; `db.create_all()` creates tables on startup and `python init_db.py` is the explicit setup command.

## Tables

### `user`
- `id` primary key
- `name`, unique `email`
- `role`: `admin`, `owner`, or `viewer`. Publicly registered users receive `owner`; the `viewer` role is retained for the dedicated read-only demo/test account and explicitly read-only accounts.
- `password_hash`: Werkzeug password hash (never the plaintext password)
- `active`, `created_at`

### `document`
- `id` primary key; `owner_id` references `user.id`
- `title`, `original_filename`, `category`, `description`
- `content`: binary file bytes in the database
- `content_type`, `size_bytes`, `sha256`
- `created_at`, `updated_at`

### `document_grant`
- `id` primary key
- `document_id` references `document.id` with cascade deletion
- `user_id` references `user.id`; `created_by_id` references `user.id`
- `permission`: `read` or `edit`; unique pair `(document_id, user_id)`
- `created_at`

### `audit_head`
- Singleton row with `id=1` and `last_hash`; locked when appending on PostgreSQL to serialize the hash chain.

### `audit_event`
- `id` primary key and unique `event_uuid`
- Actor ID/email, action, document ID, target user ID, JSON-encoded details, IP, user-agent, timestamp
- `previous_hash` and unique `event_hash`
- Audit actor/document IDs deliberately have no foreign keys, so history survives user/document deletion.

## Relationships and security notes

- One user can own many documents.
- A document can have multiple direct grants, one per target user.
- A grant never makes a document public; all read/download/edit/delete routes re-check the current user and grant.
- Document bytes are never served from a public static directory.
- Audit hashes detect many changes, but the database is not an immutable/WORM audit store. See `THREATS.md`.


## Schema migration policy

Flask-Migrate/Alembic is configured under `migrations/`. The baseline revision uses SQLAlchemy metadata `create_all(checkfirst=True)` to create missing current tables while preserving tables from the earlier starter schema. It does not perform column alterations; future schema changes must be generated, reviewed, and applied as explicit Alembic revisions. The baseline downgrade is disabled to prevent accidental destruction of stored document bytes and audit history.
