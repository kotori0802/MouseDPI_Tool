# Security Policy

## Supported versions

| Version | Status |
|---|---|
| `0.1.0rc2` (current) | Source Release Candidate — not production-supported |
| `0.1.0rc1` | First public source RC (published tag; immutable) |
| Future stable | TBD |

Treat this tree as unsupported for production liability until a stable release is published.

## Reporting a vulnerability

Prefer private disclosure to the repository owner (for example via GitHub Security Advisories, or direct contact listed by the owner).

Please include:

- Affected version / commit
- Reproduction steps
- Impact (integrity, confidentiality, availability)
- Whether Session evidence / Findings correctness is affected

Do **not** open a public issue for unfixed security-sensitive flaws if a private channel exists.

## Out of scope (typical)

- Physical mouse hardware defects
- Operator misconfiguration of distance/DPI
- Findings WARN/FAIL that correctly reflect measurement evidence
- Issues solely in ignored local `dist/` / `reports/` trees

## Evidence integrity

Manipulating capture, thresholds, or reports to force PASS is considered a security/integrity violation (see `SECURITY_CODEX.md` SC-07 / SC-12).
