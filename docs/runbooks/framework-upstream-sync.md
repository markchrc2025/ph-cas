# Framework upstream sync (Ledger side)

The framework side is docs-sentire/UPSTREAM-SYNC.md in the sentire-framework repo. The
daily Upstream watch workflow there opens an issue when Frappe or ERPNext publishes a newer
v16 tag or a security advisory.

1. Sync the framework first and tag the next release (for example v16.61.0-sentire.1).
   Do this before any ERPNext bump: ERPNext raises the Frappe version it needs.
2. In ph-cas, on a new branch, set FRAPPE_TAG (release/<release>) and FRAPPE_COMMIT in the Dockerfile and in
   scripts/bootstrap.sh; both builds stop if the branch is not at that commit, and update VERSIONS.md (tag and commit).
   Changing bootstrap.sh makes CI rebuild its bench cache.
3. Push and let CI run the full suite. Fix what fails.
4. Run the Image workflow on the branch with "publish" unticked: CI never builds the
   Dockerfile.
5. Merge when both are green. Add one line to releases.json and record the change as a
   minor enhancement (D1), unless the accountant decides it is a major version.
6. Never move a tag. A fix to a framework release gets the next -sentire.N.
