# SECURITY CODEX — Mouse DPI Tool

Immutable design/security principles for this project.  
Changes that weaken these invariants require explicit security review (SC-11).

This document is not a legal opinion.

First-party project source is released by the project owner under the MIT License.
Public example data is synthetic and does not contain employer/client qualification records.

---

## Invariants

### SC-01 NO SECRETS
No credential, private key, token, or signing material in source, history, logs, screenshots, fixtures, or release packages.

### SC-02 AUTHORIZED IP ONLY
Only code/data/docs/assets the project owner has the right to publish. Third-party components keep their own licenses and notices.

### SC-03 NO PRIVATE ENVIRONMENT LEAKAGE
No employer/client confidential information, NDA content, internal infrastructure, hostnames, or unreleased product data in the public tree.

### SC-04 PUBLIC TEST DATA IS SYNTHETIC OR SANITIZED
Real engineering / qualification Sessions are private by default. Public fixtures and `examples/` must be synthetic or sanitized.

### SC-05 UNTRUSTED INPUT IS DATA, NEVER CODE
No `eval` / `exec` / dynamic command construction from operator-controlled fields.

### SC-06 SUBPROCESS BOUNDARY IS FIXED AND REVIEWED
Raw Input helper launch uses a fixed argv (`shell=False`). User input must never become an arbitrary executable path or shell command.

### SC-07 CAPTURE INTEGRITY FAILS CLOSED
Incomplete or inconclusive capture must not become admissible Session evidence.

### SC-08 FILE OUTPUT IS EXPLICIT
Reports and Session JSON write only to operator-selected (or clearly documented) locations. Prefer atomic replace. No surprising overwrite of unrelated paths.

### SC-09 DEPENDENCY PROVENANCE IS KNOWN
Runtime dependencies have known source, version constraint, and license. See `THIRD_PARTY_LICENSES.md`.

### SC-10 RELEASE BINARIES MATCH REVIEWED SOURCE
Do not publish stale or untraceable `dist/` artifacts. Portable builds are a separate compliance gate from source publication.

### SC-11 SECURITY-SENSITIVE CHANGES REQUIRE REVIEW
Changes involving Actions, dependencies, subprocess, filesystem, serialization, HTML reporting, or release infrastructure require explicit security review.

### SC-12 NEVER MANIPULATE EVIDENCE TO MAKE RESULTS PASS
No hidden outlier removal, silent threshold widening, CPI “correction,” or Findings suppression merely to improve results.

### SC-13 MEASUREMENT SEMANTICS HONESTY
WARN/FAIL Findings are valid evidence outcomes. Do not overclaim native sensor DPI or treat Strict Accuracy WARN as a Tool defect by default.

### SC-14 NO EXTERNAL / EMPLOYER RUNTIME COUPLING
Standalone package only. No employer/client/external orchestration or shared-runtime imports at application runtime. No legacy companion-tool imports in the shipped package.

### SC-15 HUMAN-CONTROLLED RELEASE AUTHORITY
Automated assistants may inspect, edit, test, scan, and prepare repository state. The project owner must personally execute authority-bearing actions: commit authorship, release tags, remotes, pushes, repository visibility changes, release publication, and release signing. Automated attribution must not be silently injected into repository history.

---

## Scope split

| Release type | Status |
|---|---|
| Source-only GitHub | Target of first public baseline |
| Portable Qt/PySide binary | Separate redistribution/compliance gate — not claimed here |
