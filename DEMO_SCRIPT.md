# Five-minute demo recording script

Record the actual deployed application only after each step works. Do not edit together fake results or claim tests/deployment that you have not run.

## 0:00–0:30 — Introduce the design
- State that TrustVault is a document-sharing app with per-document named grants.
- Explain that the server, not the frontend, makes every authorization decision.

## 0:30–1:15 — Owner uploads a file
- Register a new account (or sign in as a normal owner account). Every new registration can own and manage its own documents.
- Upload a small sample TXT/PDF with a category and description.
- Open its detail page and show the stored SHA-256 hash and owner.

## 1:15–2:00 — Prove ungranted access is blocked
- Sign out and sign in as a different viewer who has not been granted the document.
- Show that the document is absent from their list.
- Attempt the exact document detail and download URL; show the 404 response.

## 2:00–3:00 — Grant, then revoke
- Sign in as owner and grant the viewer `read` access.
- Sign in as viewer and open/download the file.
- As owner, revoke the grant.
- As viewer, retry the same URL and show access is denied immediately.

## 3:00–3:45 — Demonstrate least privilege
- Grant `read` access again and sign in as viewer.
- Attempt edit/delete/share routes directly; show they are denied.
- If you have a separate test account with an `edit` grant, show it can edit metadata but cannot delete or share.

## 3:45–4:30 — Audit trail
- Sign in as admin and open Admin activity.
- Show upload, download, permission grant/revoke and denied-attempt records.
- Show hash-chain status. Explain accurately that this detects tampering but is not immutable against a fully privileged database operator.
- Show admin cannot read document content unless explicitly granted.

## 4:30–5:00 — Engineering evidence
- Show `THREATS.md`, `PROMPTS.md`, `API.md`, and the test suite.
- Run `python -m pytest -q` and show the real output.
- Mention the actual unfinished items listed in the submission; do not claim unimplemented features.


## Updated Manage Access and category walkthrough

- Register a normal account and upload a document; confirm the document is private by default. An admin can also upload documents they personally own.
- Open the document card and select **Manage access**.
- Grant the dedicated read-only demo viewer `read` permission, then sign in as that viewer and verify the file is reachable.
- Change the grant to `edit` and verify metadata editing is enabled but delete/share remain unavailable.
- Revoke the grant and verify the viewer’s next direct document and download requests are denied.
- Use category chips and the search filters to find documents.
- Show the audit events for upload, permission grant/change/revoke, and denied attempts.
