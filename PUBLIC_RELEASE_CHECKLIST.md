# Public Release Checklist

Executable pre-publication gate. Complete before making a private staging repository public.

## Ownership / legal (owner)

- [x] FIRST_PARTY_PROVENANCE = user-attested clean (recorded privately)
- [x] Residual ownership risk accepted by owner (recorded privately)
- [x] Root `LICENSE` (MIT) for first-party code
- [ ] No confidential organizational documents in the tracked tree

## Vendor neutrality

- [ ] No manufacturer-specific / product-family brand references in tracked tree
- [ ] No private organizational identifiers
- [ ] README positions Tool as vendor-neutral mouse / DUT validation software
- [ ] Source code contains no external shared-runtime / orchestration coupling

## Technical sanitization

- [ ] No secrets (keys, tokens, passwords, PEMs)
- [ ] No absolute personal machine paths in tracked files
- [ ] No real qualification Sessions/HTML under tracked paths (`reports/` ignored)
- [ ] No development test-history / gate artifacts in tracked tree (`_private_dev_history/` ignored)
- [ ] Golden fixtures numeric-only or synthetic metadata
- [ ] Public examples are synthetic with disclaimer
- [ ] Screenshots PUBLIC_OK or absent (prefer clean recapture)
- [ ] `dist/`, `build/`, logs, `.cursor/` ignored
- [ ] `.gitignore` reviewed

## Dependencies

- [ ] `THIRD_PARTY_LICENSES.md` current for declared deps
- [ ] Source-only: PySide6 documented as dependency (not redistributed in Git)
- [ ] Portable binary: **separate** Qt redistribution gate (not claimed by this checklist alone)

## Security docs present

- [ ] `SECURITY_CODEX.md`
- [ ] `THREAT_MODEL.md`
- [ ] `SECURITY.md`
- [ ] `PUBLIC_RELEASE_CHECKLIST.md` (this file)
- [ ] `THIRD_PARTY_LICENSES.md`
- [ ] `docs/SOFTWARE_VALIDATION.md`

## Before making the repository public

- [ ] Secret scanning / push protection
- [ ] Dependabot alerts
- [ ] Minimal Actions permissions
- [ ] Branch protection if collaborators added
- [ ] Final GitHub security review before public

## Stop rules

Do **not** push / tag / publish portable binaries while any **BLOCKER** remains for the intended scope.
