# TrustVault — Project Submission Write-Up

> **Before submission:** Review this document against the final deployed application. Replace any incomplete sections, verify all technical claims, and include only genuine test results and commit links.

## 1. Project Overview

TrustVault is a secure document-sharing web application designed to control access to documents through ownership and explicit, per-document permissions.

The application supports document uploads, document organization and search, permission management, and security-related activity logging. Its authorization model is enforced on the server so that access to a document is not determined solely by what the frontend displays.

The project focuses on confidentiality, least privilege, permission revocation, and accountability through an audit trail.

**Live application:** https://trustvault-6cba.onrender.com

**Source repository:** https://github.com/ShaikAkber321/trustvault

Verify that both links are accessible and appropriate to share before submitting.

## 2. Architecture and Technology

TrustVault uses a Flask-based web application with server-rendered pages, database-backed persistence, and cookie-based sessions.

The main application components include:

* **Authentication:** Handles account registration, login, logout, and session management.
* **Document management:** Handles uploads, metadata, document access, editing, downloading, and deletion.
* **Authorization:** Enforces ownership and document-specific permission checks.
* **Permission management:** Allows document owners to grant, change, and revoke access.
* **Audit logging:** Records security-relevant events and links audit records using hashes.
* **Database:** Stores user accounts, document metadata and content, permission grants, and audit information.
* **Testing:** Provides automated tests for important application and security behaviors.

The project uses SQLAlchemy for database access and Flask-Migrate/Alembic for schema migration management.

Confirm the final dependency list and deployment configuration before adding more implementation-specific details.

## 3. Permission Model

TrustVault uses three account roles and document-specific grants.

### Administrator

The administrator can access the administrative activity interface and inspect relevant account metadata and audit information. Administrator status does not automatically grant access to every user's document content.

### Owner

The owner manages documents they own. Depending on the implemented operation, this includes uploading, viewing, editing metadata, deleting, and granting or revoking access for other users.

### Read Permission

A user with a `read` grant can access the shared document through the application's authorized reading and download operations. This permission does not authorize editing, deletion, or sharing.

### Edit Permission

A user with an `edit` grant can perform the editing operations permitted by the application. It does not automatically grant ownership or permission to delete or share the document.

### Server-Side Enforcement and Revocation

The application checks the current user's ownership or applicable grant when handling protected document requests.

Permission changes are stored in the database. Subsequent requests use the current permission state, so revoking a grant should prevent further access that depended on that grant.

Verify these descriptions against `permissions.py`, `documents.py`, and the final route implementations.

## 4. File Uploads and Document Storage

The application validates uploaded files and applies configured file-size and file-type restrictions.

Document content is stored in the database rather than served from a public static directory. The application records metadata such as the title, filename, category, description, content type, size, and SHA-256 hash.

Upload validation reduces certain risks but does not replace malware scanning or a comprehensive file-content security analysis.

Confirm the actual accepted file types, size limits, and storage behavior against the final implementation.

## 5. Audit Trail

TrustVault records security-relevant actions, including applicable document operations, permission changes, and denied access attempts.

The audit implementation links events using hashes and maintains an audit-chain head. Verification can help identify certain modifications to recorded history.

However, a hash-linked audit trail is not equivalent to an immutable external logging system. A sufficiently privileged database operator may be able to alter records and attempt to reconstruct the chain.

This limitation is documented in `THREATS.md`.

## 6. Testing and Verification

The project includes automated tests for application behavior and security-sensitive operations.

**Final test command:**

```powershell
python -m pytest -q
```

**Actual result from the final submission version:**

* Test date: [Enter the actual date]
* Result: [Paste the actual test summary]
* Failed or skipped tests: [Report the actual result]

Do not reuse an earlier test result as proof that the final version passes. Run the suite against the version you intend to submit and record the real output.

### Security Behaviors to Verify

Record the actual results for these scenarios:

* An unauthenticated user cannot access protected document operations.
* A user without a grant cannot access another owner's document.
* A read-only grant does not permit editing, deletion, or sharing.
* An edit grant permits only the intended editing operations.
* Revoking a grant blocks subsequent requests that rely on it.
* Public registration cannot create an administrator account.
* Invalid or oversized uploads are rejected according to the configured restrictions.
* Denied access attempts are recorded where the application implements such auditing.
* Audit-chain verification reports the actual state of the recorded events.

Include only behaviors verified by the final test run or a reproducible manual test.

## 7. AI Assistance and Engineering Decisions

AI tools were used during development only to the extent documented in `PROMPTS.md` and supported by the actual development history.

The project owner is responsible for reviewing generated suggestions, understanding the final implementation, running tests, and verifying the submitted application.

For this section, include:

* The AI tools actually used.
* Representative prompts and their purpose.
* Problems discovered during review or testing.
* The corrections actually made.
* Relevant real Git commit links.
* Tests or manual checks used to verify those corrections.

Use `PROMPTS.md` as the evidence log. Do not invent prompts, errors, test outcomes, or commit references.

## 8. Known Limitations

Review each item below against the final submitted version. Retain only the limitations that are still applicable.

Potential limitations include:

* Multi-factor authentication (MFA).
* Password reset and account recovery.
* Single sign-on (SSO).
* A full user-management interface.
* Malware scanning.
* Document version history and recovery.
* External immutable audit storage.
* Group permissions, folder inheritance, and guest sharing.
* Production-grade distributed rate-limit storage.
* Additional backup, retention, and recovery controls.

Document any other known gaps that materially affect the security or usability of the submitted application.

## 9. Deployment Verification

Before submission, verify and record:

* [ ] The live application loads successfully.
* [ ] Login and logout work.
* [ ] A normal account can upload and manage its own document.
* [ ] Sharing and revocation behave as expected.
* [ ] Unauthorized document requests are denied.
* [ ] The administrative activity page behaves according to the intended role restrictions.
* [ ] Database initialization and migrations work as documented.
* [ ] The final automated test suite has been run.
* [ ] No development secrets or real personal documents are exposed.
* [ ] The repository contains the final documentation and code.
* [ ] The demo recording demonstrates the actual deployed behavior.

**Deployment notes:** [Record any deployment-specific limitations or outstanding issues.]

## 10. Conclusion

TrustVault demonstrates a document-sharing design built around explicit permissions, server-side authorization, and auditability.

The final submission should be evaluated against the actual implementation, automated test results, documented limitations, and demonstrated behavior. Any unfinished work should be stated clearly rather than presented as a completed feature.
