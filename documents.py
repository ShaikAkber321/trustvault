import hashlib
import io
import mimetypes
import zipfile
from datetime import datetime, time, timezone
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import Document, DocumentGrant, User
from audit import record_event
from permissions import can_read, can_edit, can_delete, permission_for

bp = Blueprint("documents", __name__)
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".png", ".jpg", ".jpeg", ".docx"}
ALLOWED_CATEGORIES = {"General", "Finance", "Legal", "HR", "Engineering", "Compliance", "Customer", "Operations", "Product", "Sales", "Security", "Marketing", "Research", "Other"}


def _visible_documents():
    # Query only documents the current user owns or has an explicit grant for.
    granted_ids = db.session.query(DocumentGrant.document_id).filter_by(user_id=current_user.id)
    return Document.query.filter(or_(Document.owner_id == current_user.id, Document.id.in_(granted_ids)))


def _deny(document_id, action, document=None):
    record_event(f"denied_{action}", document_id=document_id,
                 details={"reason": "not_found_or_not_authorized", "route": request.path,
                          "document_title": document.title if document else None})
    db.session.commit()
    abort(404)  # Avoid confirming whether an inaccessible document exists.


def _validate_upload(upload):
    if not upload or not upload.filename:
        raise ValueError("Choose a file to upload.")
    filename = Path(upload.filename.replace("\\", "/")).name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Allowed: PDF, TXT, CSV, PNG, JPG/JPEG and DOCX.")
    content = upload.stream.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
    if not content:
        raise ValueError("Empty files are not allowed.")
    if len(content) > current_app.config["MAX_CONTENT_LENGTH"]:
        raise ValueError("File exceeds the 5 MB upload limit.")
    if ext == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("File contents do not look like a PDF.")
        content_type = "application/pdf"
    elif ext in {".png", ".jpg", ".jpeg"}:
        if ext == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("File contents do not look like a PNG image.")
        if ext in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise ValueError("File contents do not look like a JPEG image.")
        content_type = "image/png" if ext == ".png" else "image/jpeg"
    elif ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = archive.namelist()
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise ValueError("DOCX file is missing required document parts.")
                # DOCX is a ZIP container. Bound expanded size to reduce the risk
                # of storing an archive designed to expand to an extreme size.
                if len(names) > 5000 or sum(item.file_size for item in archive.infolist()) > 25 * 1024 * 1024:
                    raise ValueError("DOCX archive expands beyond the allowed safety limit.")
        except zipfile.BadZipFile:
            raise ValueError("File contents do not look like a valid DOCX document.")
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        try:
            decoded = content.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("TXT and CSV files must be UTF-8 text.")
        if "\x00" in decoded:
            raise ValueError("Binary content is not allowed in TXT or CSV files.")
        content_type = "text/csv" if ext == ".csv" else "text/plain; charset=utf-8"
    return filename[:255], content, content_type


@bp.get("/")
@login_required
def index():
    query = _visible_documents()
    scope = request.args.get("scope", "").strip()
    if scope == "shared":
        # This view contains only documents explicitly shared with the current
        # user and excludes their own documents. It does not change authorization.
        shared_ids = db.session.query(DocumentGrant.document_id).filter_by(user_id=current_user.id)
        query = query.filter(Document.owner_id != current_user.id, Document.id.in_(shared_ids))
    name = request.args.get("name", "").strip()
    owner = request.args.get("owner", "").strip()
    category = request.args.get("category", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    if name:
        query = query.filter(or_(Document.title.ilike(f"%{name}%"), Document.original_filename.ilike(f"%{name}%")))
    if owner:
        query = query.join(User, Document.owner_id == User.id).filter(or_(User.name.ilike(f"%{owner}%"), User.email.ilike(f"%{owner}%")))
    if category in ALLOWED_CATEGORIES:
        query = query.filter(Document.category == category)
    try:
        if date_from:
            start = datetime.combine(datetime.strptime(date_from, "%Y-%m-%d").date(), time.min).replace(tzinfo=timezone.utc)
            query = query.filter(Document.created_at >= start)
        if date_to:
            end = datetime.combine(datetime.strptime(date_to, "%Y-%m-%d").date(), time.max).replace(tzinfo=timezone.utc)
            query = query.filter(Document.created_at <= end)
    except ValueError:
        flash("Dates must use YYYY-MM-DD.", "warning")
    page = request.args.get("page", 1, type=int)
    page = max(1, page or 1)
    pagination = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    docs = pagination.items
    pagination_args = request.args.to_dict()
    pagination_args.pop("page", None)
    def page_url(page_number):
        params = dict(pagination_args)
        params["page"] = page_number
        return url_for("documents.index", **params)
    # Category tiles reflect only documents this account is allowed to see.
    all_visible_docs = _visible_documents().all()
    category_counts = {category_name: sum(1 for item in all_visible_docs if item.category == category_name)
                       for category_name in ALLOWED_CATEGORIES}
    owned_count = Document.query.filter_by(owner_id=current_user.id).count()
    shared_count = Document.query.join(DocumentGrant, DocumentGrant.document_id == Document.id).filter(
        DocumentGrant.user_id == current_user.id).count()
    return render_template("index.html", documents=docs, permission_for=permission_for,
                           categories=sorted(ALLOWED_CATEGORIES), category_counts=category_counts,
                           owned_count=owned_count, shared_count=shared_count, visible_count=len(all_visible_docs),
                           pagination=pagination, total_results=pagination.total,
                           prev_url=page_url(pagination.prev_num) if pagination.has_prev else None,
                           next_url=page_url(pagination.next_num) if pagination.has_next else None)


@bp.route("/documents/upload", methods=["GET", "POST"])
@login_required
def upload():
    # Normal accounts own the files they upload. Admin status does not grant access
    # to other people's documents; a document is owned by its uploader.
    if current_user.role not in {"owner", "admin"}:
        record_event("denied_upload", details={"reason": "role_not_allowed", "role": current_user.role})
        db.session.commit()
        abort(403)
    if request.method == "POST":
        try:
            filename, content, content_type = _validate_upload(request.files.get("file"))
            title = request.form.get("title", "").strip()
            category = request.form.get("category", "General").strip()
            description = request.form.get("description", "").strip()
            if not title or len(title) > 180:
                raise ValueError("Title is required and must be 180 characters or fewer.")
            if category not in ALLOWED_CATEGORIES:
                raise ValueError("Choose a valid category.")
            if len(description) > 1000:
                raise ValueError("Description must be 1,000 characters or fewer.")
            doc = Document(title=title, original_filename=filename, category=category,
                           description=description, owner_id=current_user.id, content=content,
                           content_type=content_type, size_bytes=len(content),
                           sha256=hashlib.sha256(content).hexdigest())
            db.session.add(doc)
            db.session.flush()
            record_event("document_uploaded", document_id=doc.id,
                         details={"title": title, "filename": filename, "size_bytes": len(content), "sha256": doc.sha256})
            db.session.commit()
            flash("Document uploaded.", "success")
            return redirect(url_for("documents.detail", document_id=doc.id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("upload.html", categories=sorted(ALLOWED_CATEGORIES))


@bp.get("/documents/<int:document_id>")
@login_required
def detail(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_read(current_user, doc):
        _deny(document_id, "read", doc)
    record_event("document_viewed", document_id=doc.id, details={"title": doc.title})
    db.session.commit()
    grants = DocumentGrant.query.filter_by(document_id=doc.id).all() if can_delete(current_user, doc) else []
    candidates = User.query.filter(User.id != current_user.id, User.active.is_(True)).order_by(User.name.asc()).all() if can_delete(current_user, doc) else []
    return render_template("detail.html", document=doc, grants=grants, candidates=candidates,
                           permission=permission_for(current_user, doc), can_edit=can_edit(current_user, doc),
                           can_delete=can_delete(current_user, doc))


@bp.get("/documents/<int:document_id>/share")
@login_required
def share(document_id):
    """Dedicated Manage Access screen; only the document owner can change grants."""
    doc = db.session.get(Document, document_id)
    if not doc or not can_delete(current_user, doc):
        _deny(document_id, "manage_access", doc)
    grants = DocumentGrant.query.filter_by(document_id=doc.id).order_by(DocumentGrant.created_at.desc()).all()
    candidates_query = User.query.filter(User.id != current_user.id, User.active.is_(True))
    granted_user_ids = [grant.user_id for grant in grants]
    if granted_user_ids:
        candidates_query = candidates_query.filter(User.id.notin_(granted_user_ids))
    candidates = candidates_query.order_by(User.name.asc()).all()
    return render_template("manage_access.html", document=doc, grants=grants, candidates=candidates)


@bp.get("/documents/<int:document_id>/download")
@login_required
def download(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_read(current_user, doc):
        _deny(document_id, "download", doc)
    record_event("document_downloaded", document_id=doc.id,
                 details={"title": doc.title, "filename": doc.original_filename, "sha256": doc.sha256})
    db.session.commit()
    return send_file(io.BytesIO(doc.content), mimetype=doc.content_type,
                     as_attachment=True, download_name=doc.original_filename, max_age=0)


@bp.route("/documents/<int:document_id>/edit", methods=["GET", "POST"])
@login_required
def edit(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_edit(current_user, doc):
        _deny(document_id, "edit", doc)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        if not title or len(title) > 180 or category not in ALLOWED_CATEGORIES or len(description) > 1000:
            flash("Enter a valid title, category and description.", "danger")
        else:
            before = {"title": doc.title, "category": doc.category, "description": doc.description}
            doc.title, doc.category, doc.description = title, category, description
            record_event("document_changed", document_id=doc.id, details={"before": before, "after": {"title": title, "category": category, "description": description}})
            db.session.commit()
            flash("Document details updated.", "success")
            return redirect(url_for("documents.detail", document_id=doc.id))
    return render_template("edit.html", document=doc, categories=sorted(ALLOWED_CATEGORIES))


@bp.post("/documents/<int:document_id>/delete")
@login_required
def delete(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_delete(current_user, doc):
        _deny(document_id, "delete", doc)
    details = {"title": doc.title, "filename": doc.original_filename, "sha256": doc.sha256}
    # Preserve the audit event before deleting the document row and its grants.
    record_event("document_deleted", document_id=doc.id, details=details)
    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("documents.index"))


@bp.post("/documents/<int:document_id>/grants")
@login_required
def grant_access(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_delete(current_user, doc):
        _deny(document_id, "grant_permission", doc)
    email = request.form.get("email", "").strip().lower()
    permission = request.form.get("permission", "read").strip()
    target = User.query.filter_by(email=email, active=True).first()
    if not target:
        flash("Choose an existing active user.", "danger")
    elif target.id == current_user.id:
        flash("You already own this document.", "warning")
    elif permission not in {"read", "edit"}:
        flash("Permission must be read or edit.", "danger")
    else:
        grant = DocumentGrant.query.filter_by(document_id=doc.id, user_id=target.id).first()
        old_permission = grant.permission if grant else None
        if grant:
            grant.permission = permission
        else:
            db.session.add(DocumentGrant(document_id=doc.id, user_id=target.id,
                                         permission=permission, created_by_id=current_user.id))
        record_event("permission_granted" if not old_permission else "permission_changed",
                     document_id=doc.id, target_user_id=target.id,
                     details={"target_email": target.email, "old_permission": old_permission, "new_permission": permission})
        db.session.commit()
        flash(f"{permission.title()} access saved for {target.email}.", "success")
    return redirect(url_for("documents.share", document_id=doc.id))


@bp.post("/documents/<int:document_id>/grants/<int:grant_id>/revoke")
@login_required
def revoke_access(document_id, grant_id):
    doc = db.session.get(Document, document_id)
    if not doc or not can_delete(current_user, doc):
        _deny(document_id, "revoke_permission", doc)
    grant = DocumentGrant.query.filter_by(id=grant_id, document_id=doc.id).first_or_404()
    target_id, target_email, old_permission = grant.user_id, grant.user.email, grant.permission
    record_event("permission_revoked", document_id=doc.id, target_user_id=target_id,
                 details={"target_email": target_email, "old_permission": old_permission})
    db.session.delete(grant)
    db.session.commit()
    flash(f"Access revoked for {target_email}.", "success")
    return redirect(url_for("documents.share", document_id=doc.id))
