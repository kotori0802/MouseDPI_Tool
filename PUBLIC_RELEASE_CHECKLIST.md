# Public Release Checklist

Executable pre-publication gate. Complete **before** `git init` of a public baseline, and again before making a private staging repo public.

## Ownership / legal (owner)

- [x] FIRST_PARTY_PROVENANCE = user-attested clean (recorded privately)
- [x] Available dispatch documents: no relevant IP-assignment provision identified; residual ownership risk accepted by owner
- [x] Root `LICENSE` (MIT) for first-party code
- [ ] No confidential client/agency documents in the tracked tree

## Vendor neutrality

- [ ] No manufacturer-specific / product-family brand references in tracked tree
- [ ] No employer/client identifiers
- [ ] README positions Tool as vendor-neutral mouse / DUT validation software
- [ ] Source code contains no employer-specific runtime coupling

## Technical sanitization

- [ ] No secrets (keys, tokens, passwords, PEMs)
- [ ] No `C:\Users\...` / absolute personal paths in tracked files
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

## After private GitHub staging (do not enable prematurely)

- [ ] Secret scanning / push protection
- [ ] Dependabot alerts
- [ ] Minimal Actions permissions
- [ ] Branch protection if collaborators added
- [ ] Final GitHub security review before public

## Stop rules

Do **not** `git init` / push / tag / publish portable binaries while any **BLOCKER** remains for the intended scope.
