# TrustVault - Five-Minute Demo Recording Script

## Recording Guidelines

* Demonstrate the actual deployed application.
* Verify each step before recording.
* Use separate test accounts to demonstrate ownership, sharing, and access denial.
* Never expose real personal documents, passwords, or production secrets.
* Show actual test results and do not claim features that have not been implemented or verified.

## 0:00-0:30 - Introduction and Security Design

**Demonstrate:** Open the deployed TrustVault application.

**Explain:**

* TrustVault is a secure document-sharing application with document-specific access permissions.
* Document owners can grant and revoke `read` and `edit` permissions for individual users.
* The server enforces authorization rather than relying on frontend visibility alone.
* Security-relevant actions are recorded in an audit trail.

## 0:30-1:15 - Owner Registration and Document Upload

**Demonstrate:**

1. Register a new account or sign in using a normal owner account.
2. Upload a small, non-sensitive TXT or PDF sample.
3. Add a title, category, and description.
4. Open the document details page.

**Explain:**

* Newly registered users receive the normal owner role.
* The uploader owns the uploaded document.
* Documents are private by default unless access is explicitly granted.
* Show the document's SHA-256 hash if it is displayed by the application.

**Expected result:** The owner can view the uploaded document.

## 1:15-2:00 - Verify Unauthorized Access Is Denied

**Demonstrate:**

1. Sign out of the owner account.
2. Sign in using a separate account that has not been granted access.
3. Show that the private document is absent from the account's visible document list.
4. Attempt to access the document's detail or download URL directly, using its actual ID.

**Explain:**

* Hiding a document from the interface is not the security boundary.
* The server checks ownership and current permissions when handling document requests.

**Expected result:** The unauthorized request is denied. If the application returns HTTP 404 for inaccessible documents, show the actual 404 response.

## 2:00-3:00 - Grant and Revoke Access

**Demonstrate:**

1. Sign back in as the document owner.
2. Open **Manage access** for the uploaded document.
3. Grant the separate test account `read` permission.
4. Sign in as that account and open or download the document.
5. Return to the owner account and revoke the grant.
6. Sign back in as the viewer and retry the same document URL.

**Explain:**

* Access is granted for a specific document and user.
* The server checks current permissions when a request is made.
* Revoking a grant should block subsequent requests that depend on that grant.

**Expected result:** The viewer can access the document while the grant is active, but access is denied after revocation.

## 3:00-3:45 - Demonstrate Least Privilege

**Demonstrate:**

1. Grant the test account `read` access again.
2. Verify that reading is allowed.
3. Attempt an edit, delete, or sharing action using the viewer account.
4. If a separate test account has `edit` permission, demonstrate its actual permitted operations.

**Explain:**

* `read` permission allows reading but not editing, deleting, or sharing.
* `edit` permission allows the editing operations implemented by the application.
* Ownership and sharing controls remain restricted to the document owner.

**Expected result:** Each action succeeds or fails according to the implemented permission rules. Show the actual result rather than assuming an operation is blocked.

## 3:45-4:30 - Audit Trail and Administrator Restrictions

**Demonstrate:**

1. Sign in using the admin account.
2. Open the Admin activity page.
3. Show relevant audit records, such as uploads, downloads, permission changes, revocations, and denied attempts, if present.
4. Show the audit-chain verification result.
5. If practical, demonstrate that administrator status alone does not grant access to another user's document content.

**Explain:**

* The audit trail records relevant security events.
* Hash linking helps detect certain modifications to audit history.
* The hash chain is not an immutable audit system and cannot protect against every action by a fully privileged database operator.
* Administrative access to audit information does not automatically grant document-content access.

**Expected result:** Show the actual audit events and verification status produced by the application.

## 4:30-5:00 - Engineering Evidence and Wrap-Up

**Demonstrate:**

1. Briefly show `README.md`, `API.md`, `SCHEMA.md`, `THREATS.md`, and `PROMPTS.md`.
2. Show the automated test suite.
3. Run the tests and display the real output:

```powershell
python -m pytest -q
```

4. Mention any remaining limitations that are relevant to the submission.

**Closing points:**

* TrustVault implements document ownership and explicit document-level permissions.
* Authorization decisions are enforced on the server.
* The project includes automated tests and security documentation.
* The remaining limitations are documented in `THREATS.md`.

Only state that the tests pass if the displayed test run confirms it.

## Optional Additional Walkthrough

If time permits, demonstrate these features after the main recording or include a brief supplementary clip:

* Use category filters and search to locate documents.
* Show the Manage access page.
* Change a grant from `read` to `edit`, if supported by the interface.
* Verify the actual editing restrictions for an `edit` grant.
* Revoke access and retry a document request.
* Show corresponding audit events, if recorded.

## Final Recording Checklist

* [ ] The deployed application loads successfully.
* [ ] Separate test accounts are available.
* [ ] The sample document contains no sensitive information.
* [ ] Upload and document viewing work.
* [ ] Unauthorized access is denied.
* [ ] Granting and revoking permissions work.
* [ ] Role restrictions are demonstrated accurately.
* [ ] Audit records and verification status are shown accurately.
* [ ] The actual automated test output is visible.
* [ ] No passwords, secrets, or personal documents are exposed.
* [ ] The recording and submission claims match the demonstrated behavior.
