"""Append-only application audit events with a tamper-evident hash chain.

This detects many edits/deletions/reordering of events; it is not a substitute for
external immutable storage if an attacker controls the database and its head row.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from flask import request, has_request_context
from flask_login import current_user
from sqlalchemy import select
from extensions import db
from models import AuditEvent, AuditHead


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def record_event(action, document_id=None, target_user_id=None, details=None, actor=None):
    """Append an audit event in the caller's current DB transaction."""
    if actor is None:
        actor = current_user if has_request_context() and current_user.is_authenticated else None
    # Ensure the singleton exists. The row lock serializes writers on PostgreSQL.
    head = db.session.execute(select(AuditHead).where(AuditHead.id == 1).with_for_update()).scalar_one_or_none()
    if head is None:
        head = AuditHead(id=1, last_hash="0" * 64)
        db.session.add(head)
        db.session.flush()
    previous_hash = head.last_hash
    now = datetime.now(timezone.utc).isoformat()
    event_uuid = str(uuid.uuid4())
    actor_id = actor.id if actor else None
    actor_email = actor.email if actor else "anonymous"
    ip = request.remote_addr or "" if has_request_context() else ""
    ua = request.headers.get("User-Agent", "")[:300] if has_request_context() else ""
    details_json = _canonical(details or {})
    payload = {
        "event_uuid": event_uuid, "actor_id": actor_id, "actor_email": actor_email,
        "action": action, "document_id": document_id, "target_user_id": target_user_id,
        "details": details_json, "ip_address": ip, "user_agent": ua,
        "created_at": now, "previous_hash": previous_hash,
    }
    event_hash = hashlib.sha256((previous_hash + _canonical(payload)).encode("utf-8")).hexdigest()
    event = AuditEvent(
        event_uuid=event_uuid, actor_id=actor_id, actor_email=actor_email,
        action=action, document_id=document_id, target_user_id=target_user_id,
        details=details_json, ip_address=ip, user_agent=ua,
        created_at=datetime.fromisoformat(now), previous_hash=previous_hash,
        event_hash=event_hash,
    )
    db.session.add(event)
    head.last_hash = event_hash
    db.session.flush()
    return event


def verify_audit_chain(events=None):
    """Return (valid, reason); expects events in ascending id order."""
    events = list(events if events is not None else AuditEvent.query.order_by(AuditEvent.id.asc()).all())
    previous_hash = "0" * 64
    for event in events:
        if event.previous_hash != previous_hash:
            return False, f"Broken previous-hash link at event {event.id}"
        created = event.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        payload = {
            "event_uuid": event.event_uuid, "actor_id": event.actor_id,
            "actor_email": event.actor_email, "action": event.action,
            "document_id": event.document_id, "target_user_id": event.target_user_id,
            "details": event.details, "ip_address": event.ip_address,
            "user_agent": event.user_agent, "created_at": created.isoformat(),
            "previous_hash": event.previous_hash,
        }
        calculated = hashlib.sha256((previous_hash + _canonical(payload)).encode("utf-8")).hexdigest()
        if calculated != event.event_hash:
            return False, f"Hash mismatch at event {event.id}"
        previous_hash = event.event_hash
    # Check the independent head row as well. Without this comparison an attacker
    # could alter only AuditHead.last_hash and the event sequence would still pass.
    head = db.session.get(AuditHead, 1)
    if head is None:
        if events:
            return False, "Audit head is missing"
        if previous_hash != "0" * 64:
            return False, "Empty audit chain has an unexpected terminal hash"
        return True, "Empty audit chain verified"
    if head.last_hash != previous_hash:
        return False, "Audit head does not match the final event hash"
    return True, "Audit chain and head verified"
