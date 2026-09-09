# Legacy Reference Policy

## Provenance (user attestation)

- `MouseDPI_v0.4.1` is the project owner's earlier prototype (user-attested first-party work).
- Original prototype sources remain under the owner's control.
- Golden fixtures under `tests/fixtures/golden/` were frozen from that prototype for regression parity only.
- This document records engineering policy; it is not a legal ownership determination.

## Policy

- Immutable golden reference package lives beside this repo (typically `MouseDPI_v0.4.1`).
- Pass `--legacy-root` or `MOUSEDPI_LEGACY_ROOT` to `tools/_generate_legacy_golden_fixtures.py`. Do not put machine paths in `pyproject.toml`.
- New project **must not** import legacy companion modules, external orchestration/shared-runtime packages, or `dpi_step_tool` at **runtime**.
- Golden fixtures under `tests/fixtures/golden/` were generated from legacy **only**.
- Do not regenerate expected golden fixtures from `mouse_dpi_tool` outputs.
- The fixture generator is a **dev-only** script; it is the sole allowed legacy importer.

## Public-data note

- Golden fixtures contain synthetic numeric regression inputs/expected values — not product validation evidence.
- Do not embed private organization or product identifiers, hostnames, or absolute personal paths in fixtures or this tree.

## configured_dpi compatibility

- Canonical V1 field: `configured_dpi`
- Legacy alias: `target_dpi` (same number, not a second truth)
- Ingest: `resolve_configured_dpi()` / trial readers accept `target_dpi`
- Emit: measurement objects and Session JSON use `configured_dpi` only
- Golden tests project through `as_legacy_trial` / `as_legacy_group`
