# Reference assets

Points at the in-package manual observation template:

`src/mouse_dpi_tool/resources/templates/manual_observation_template.json`

Load via `mouse_dpi_tool.resources.manual_observation_template()`.

No third-party binaries, confidential documents, or proprietary screenshots are stored under `reference/`.

## Regenerating golden fixtures (rare)

Golden fixtures under `tests/fixtures/golden/` are frozen from the owner-controlled
legacy prototype for regression parity. Do not regenerate expected fixtures from
`mouse_dpi_tool` outputs.

```powershell
python tools\_generate_legacy_golden_fixtures.py --legacy-root <path-to-MouseDPI_v0.4.1>
```

Legacy golden reference (immutable): `--legacy-root` / `MOUSEDPI_LEGACY_ROOT`

See also `LEGACY.md` for policy.
