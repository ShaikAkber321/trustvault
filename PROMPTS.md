# AI-assisted development log

Keep this file current during development. Entries below record the initial scaffold and checks performed for this generated starter. Add the actual date, observed defect, your own correction, and the real commit hash/link after you run each check and commit. Do not claim a defect was fixed until you reproduce and verify it.

## 2026-10-24 — Project architecture and initial implementation
- **Tool/prompt:** ChatGPT; asked to build TrustVault from the supplied challenge statement, with a Render-friendly deployment plan, named per-document grants, server-side authorization, audit logging, tests, and documentation.
- **Produced:** Flask application with SQLAlchemy models, login sessions, per-document permission checks, database-backed file content, hash-chained audit events, templates, tests, and Render configuration.
- **Review focus / potential issue:** Generated code is not trusted by default. In particular, check every direct document route for IDOR, ensure an admin role does not bypass document grants, verify revoked grants are re-checked on each request, and test the audit chain against modified records.
- **What I did instead:** Added explicit `can_read`, `can_edit`, and owner-only `can_delete` functions; recorded denied access attempts; added security tests. **Run the tests and replace this note with the actual issues found and verified fixes.**
- **Commit:** Add the real commit link after committing this work; do not invent a commit hash.

## 2026-10-24 — Authorization review (required evidence entry 1)
- **Tool/prompt:** ChatGPT; requested a security review of document detail/download/edit/delete and grant/revoke endpoints for direct-object-reference and privilege-escalation risks.
- **Produced:** Route handlers call server-side permission helpers for each request; inaccessible resources return 404 to reduce document-ID enumeration.
- **Review focus / potential issue:** A hidden frontend button would not enforce authorization, and an `edit` grant must not automatically imply delete or sharing rights.
- **What I did instead:** Implemented server-side checks independently of UI visibility and tests that try direct URL/POST access as a read-only user. Record any additional real bug found during execution here.
- **Commit:** Add the real commit link after committing this review/fix.

## 2026-10-24 — Audit-chain review (required evidence entry 2)
- **Tool/prompt:** ChatGPT; requested an audit trail for uploads, downloads, changes, deletion, permission changes, and refused access attempts, with tamper detection.
- **Produced:** Audit events link to the prior event hash; admin page verifies the chain; test mutates a stored event and expects verification to fail.
- **Review focus / potential issue:** A hash chain is not immutable if an attacker can rewrite the database and head row; silently claiming it is impossible to tamper with would be incorrect.
- **What I did instead:** Documented the limit explicitly and listed external append-only/WORM log anchoring as a production improvement. Run the test and record its actual result.
- **Commit:** Add the real commit link after committing this review/fix.

## 2026-10-24 — File validation review
- **Tool/prompt:** ChatGPT; requested validation for untrusted file uploads with a strict size limit and supported formats.
- **Produced:** Extension allowlist, 5 MB limit, PDF/image signatures, DOCX ZIP structure checks, UTF-8 checks for TXT/CSV, and attachment downloads.
- **Review focus / potential issue:** An extension and browser-provided MIME type alone can be spoofed; format checks also do not prove a file is safe from malware.
- **What I did instead:** Added server-side content checks and a malformed-PDF test; documented malware scanning as an unimplemented limitation. Run tests with mismatched file contents and add actual findings.
- **Commit:** Add the real commit link after committing this review/fix.

## 2026-10-24 — Deployment and persistence review
- **Tool/prompt:** ChatGPT; requested a deployment plan suitable for Render and a README that a fresh clone can run.
- **Produced:** PostgreSQL URL support, `render.yaml`, health endpoint, Gunicorn Procfile, `.env.example`, setup instructions, and database-backed file bytes.
- **Review focus / potential issue:** A free web service's local filesystem may be ephemeral; storing uploaded files only in local paths can lose data after restart/redeploy. Known demo passwords must not be treated as production secrets.
- **What I did instead:** Store file bytes in PostgreSQL for this small challenge scope and require unique environment-configured demo passwords on Render. Verify the deployment using an incognito window and document the result.
- **Commit:** Add the real commit link after committing this review/fix.

## Reusable review instructions
- Ask AI to identify authorization bypasses, but require a route-by-route explanation and a test for every claimed fix.
- Never accept generated security claims without reading the relevant functions and running tests.
- Keep real dates and commit links. Do not backdate commits or invent AI mistakes.


## 2026-10-24 — Registration, account provisioning, and glass UI (verify locally before finalizing)
- **Tool/prompt:** ChatGPT; asked to add a sign-up option, make document upload easier to find/use, and give TrustVault a polished glassmorphism theme.
- **Produced:** Viewer-only public registration, admin provisioning for owner/viewer accounts, a redesigned glass-style workspace, and a drag-and-drop upload form.
- **What was wrong in the previous version:** There was no public registration route. Upload was only available to the seeded `owner` role, so a person who signed in as the seeded viewer could not upload. A naive sign-up implementation with a role selector would let people assign themselves owner/admin privileges.
- **What changed:** `/register` always creates `viewer` regardless of submitted form fields; `/admin/users/new` lets admins create `owner` or `viewer` accounts but rejects `admin`; both actions are audited. Added tests for role escalation and admin-only owner provisioning.
- **Verification status:** Python syntax compilation passed in the generation environment. The pytest suite could not be run here because Flask is not installed in that environment; run `python -m pytest -q` in the project virtual environment and record the real result. Visually verify registration, admin provisioning, upload, and responsive layout locally.
- **Commit:** Add the real commit URL after committing these changes from your own repository; do not invent a hash.


## 2026-10-24 — Fix discoverability, document sharing workflow, and glass UI

- **Request to the AI:** Review the running TrustVault experience and make document upload discoverable, add a dedicated Manage Access screen similar in workflow to the supplied `/documents/<id>/share` reference, improve category navigation, and refine the glassmorphism UI.
- **What the tool changed:** Added a dedicated `/documents/<id>/share` page, category chips and more categories, an explicit Manage access card action, improved animated glass surfaces, and allowed administrators to upload documents they own.
- **What needed careful review:** Upload was only available to `owner` accounts, so an administrator who signed in could see search but no upload action. Publicly registered users remain viewers by design, so registration does not automatically grant upload privileges. A broad admin bypass would have been dangerous; instead, the admin can manage only documents they personally upload and does not gain access to other users' documents. Manage Access remains owner-only.
- **What was done instead:** Kept server-side checks; updated the nav/dashboard to show Add document to owners and admins; added tests that an admin's own document is not visible to a different owner and that the Manage Access page is owner-only. Added the dedicated grant/revoke interface and category navigation.
- **Verification status:** Python syntax/template source review only so far. Run the project test suite locally and record actual outcomes before claiming this works in deployment.
- **Commit:** Add the real GitHub commit URL here after committing these changes. Do not invent a commit URL.


## 2026-10-24 — Change account ownership model and improve visual hierarchy
- **Tool/prompt:** ChatGPT; asked to make every public registrant a normal user who can own/upload/manage their own documents, share them selectively, and refresh the frontend with a premium iPhone-inspired glass theme, larger typography, animations, and prominent categories.
- **Produced:** Registration now creates `owner` regardless of any submitted role; admin account provisioning also creates only normal owner accounts; legacy non-demo viewer accounts are migrated to owner on startup; the workspace has large category tiles with counts, bigger type, animated liquid-glass cards, improved stats, and a clearer upload action.
- **What was wrong in the previous implementation:** Registration assigned `viewer`, and the UI/backend correctly hid/blocked upload for that role, so a person registering with their own email could not use the core document-owner workflow. Category chips were small and horizontally scrolling, making categories hard to discover; base text sizes were also too small for comfortable use.
- **What I changed and must verify:** Changed the role assignment in `auth.py`, added a legacy-role migration in `app.py`, updated registration/login/dashboard templates and CSS, and changed the registration test to prove a newly registered account can upload its own document while forged `admin` role input is ignored. Run the full tests and manually verify upload, sharing, revocation, category filters, responsive behaviour, and that unrelated users still cannot access private documents.
- **Commit:** Add the real commit URL after committing this change in your own repository. Do not invent a commit hash.


## 2026-10-24 — Force explicit authentication before the workspace
- **Tool/prompt:** ChatGPT; asked to review the whole app because the workspace appeared immediately and the user was concerned that uploads might be available before login. Requested strict challenge-level authorization and a more vivid, readable glass interface.
- **What the tool found:** The workspace and document routes already used Flask-Login, but successful public registration automatically logged the new account in and redirected straight to the workspace. That behaviour made the app look as if it skipped the login screen. The old browser session cookie could also preserve an authenticated session across the update.
- **What was changed:** Registration now creates an owner account and redirects to the login page without authenticating the new session; the session cookie name was versioned to invalidate old cookies; tests were added for anonymous access to private routes and for forged `role=admin` registration. Production demo seeding now refuses known fallback passwords when Render/production is detected and seed secrets are absent/too short. The theme was changed to high-contrast midnight aurora glass with larger type and violet/cyan/mint accents.
- **What still needs verification:** Run `python -m pytest -q`, then test in an incognito window: `/` redirects to `/login`; registration redirects to login; after explicit login, uploads, direct document URLs, access grants and revocation behave as expected. Do not claim the tests pass until their output confirms it.
- **Commit:** Add the real commit URL after committing these actual changes in your own repository; do not invent a hash or backdate history.


## 2026-10-24 — Final security and contrast review
- **Request / prompt summary:** Review the current Aurora Secure Edition for the previously identified issues: selected category tiles become light while their labels stay white; strengthen login/registration throttling, audit-chain head verification, browser security headers, database initialization, and tests. Also add a clear “Shared with me” view.
- **What the tool produced:** A focused patch to CSS, Flask setup/authentication, audit verification, DOCX validation, migration scaffolding, tests, and documentation.
- **What was wrong in the existing implementation:** The older `.category-card.selected` rule applied a pale background but later dark-theme overrides left the label white, reducing contrast. Audit verification validated event hashes/links but did not compare the terminal event hash to `AuditHead.last_hash`. The README still described rate limiting as not implemented, and database initialization was performed on app creation, which can race across multiple Gunicorn workers.
- **What I changed instead:** Added an explicit dark selected-category background and readable selected text; compared the computed terminal hash with the stored head; added login and registration rate limits, security response headers, a bounded expanded DOCX archive size, tests for head tampering, rate limiting, headers, and CSRF; added Flask-Migrate baseline support and moved database initialization/seeding to an explicit startup step before the web worker. Added a “Shared with me” view.
- **Verification:** Python syntax compilation and ZIP integrity are checked during packaging. Full pytest execution was not possible in the build environment because dependency installation could not reach the package index. Run `python -m pytest -q` locally and record the actual result before submission.
- **Commit link:** Add the real commit URL after committing this patch in your own repository. Do not fabricate a commit hash or backdate it.
