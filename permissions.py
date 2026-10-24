from models import DocumentGrant


def permission_for(user, document):
    """Return owner/read/edit/None. Admins do not gain document access by role."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    if document.owner_id == user.id:
        return "owner"
    grant = DocumentGrant.query.filter_by(document_id=document.id, user_id=user.id).first()
    return grant.permission if grant else None


def can_read(user, document):
    return permission_for(user, document) in {"owner", "read", "edit"}


def can_edit(user, document):
    return permission_for(user, document) in {"owner", "edit"}


def can_delete(user, document):
    # Deletion is intentionally owner-only; edit grants do not imply delete.
    return bool(user and getattr(user, "is_authenticated", False) and document.owner_id == user.id)
