# Security Policy

## Supported versions

Until a public release is tagged, treat the development tree as **unsupported for production liability**.  
When releases exist, this section will list supported version ranges.

| Version | Supported |
|---|---|
| `0.1.0rc1` (current) | Source Release Candidate |
| Future stable | TBD after private GitHub staging / publication gates |

## Reporting a vulnerability

Prefer private disclosure to the repository owner (GitHub Security Advisories once the repo exists, or direct contact listed by the owner).

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
