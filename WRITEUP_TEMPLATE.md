# TrustVault — short submission write-up (complete honestly after testing)

## What I built
TrustVault is a document-sharing web app with direct per-document read/edit grants, validated uploads, server-side authorization, and a searchable audit trail.

## What I deliberately did not build
Complete this list based on the version you actually deploy. Current known omissions: MFA, password reset, SSO, user-management UI, malware scanning, rate limiting, document versions/recovery, external immutable audit storage, folder/group inheritance, and guest sharing.

## Permission model in my own words
Rewrite this in your own words after reading `permissions.py` and `documents.py`. Explain the difference between owner, read, edit, and admin; mention why every route re-checks permissions and why revoke affects the next request.

## AI use and corrections
List the AI tools actually used, the real mistakes or rejected approaches you found, the tests you ran, and links to the commits that contain your fixes. Use `PROMPTS.md` as the evidence log.

## What remains unfinished
List only real gaps in the submitted version. Do not claim a deployment/test succeeded until you personally verify it.
