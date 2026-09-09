# Mouse DPI Tool

Standalone, **vendor-neutral** desktop engineering tool for mouse DPI measurement and
evidence reporting — Effective CPI validation via native Windows Raw Input and a known
physical travel distance.

Designed to turn repeatable mouse movement measurements into structured engineering
evidence for any compatible mouse / device under test (DUT).

**Canonical report language:** English (UI may localize display labels only)

## Public data & security

- First public baseline is **source-only** (no `dist/` / bundled Qt binaries in Git).
- Public fixtures and `examples/` are **synthetic**. Private qualification Sessions stay local (`reports/` is ignored).
- First-party project source is released by the project owner under the MIT License. Public example data is synthetic and does not contain employer/client qualification records.
- See `SECURITY_CODEX.md`, `THREAT_MODEL.md`, `SECURITY.md`, `PUBLIC_RELEASE_CHECKLIST.md`, `THIRD_PARTY_LICENSES.md`, and `docs/SOFTWARE_VALIDATION.md`.

## Hard rules

- Standalone package only — no employer/client/external shared-runtime or orchestration coupling
- Canonical DPI field: `configured_dpi` (legacy `target_dpi` is ingest-only)
- No single Overall PASS/WARN/FAIL verdict in V1 machine schema
- Path metrics owned only by `path_quality/`
- Theme / locale preferences are **not** Session engineering evidence
- Qt/UI never computes CPI, groups, ratios, or Findings status
- No Qt imports in `measurement/`, `capture/`, `path_quality/`, `session/`, `findings/`

## Measurement Method

V1 formal Effective CPI supports **two geometries** (Session `movement_mode`):

| Geometry (UI) | Storage `movement_mode` | Primary counts |
|---|---|---|
| **Fixture Vector** (default Qt operator) | `Vector Magnitude` | \(\sqrt{dx^2+dy^2}\) |
| **Directional Axis** | `Axis Projection` | `|dx|` or `|dy|` |

### Fixture Vector (lab any-angle straight line)

Known physical distance + continuous straight stroke at any angle + Raw Input net counts.
Official CPI = vector magnitude / inch. Signed X+/Y+ direction is **not** an admission gate.
Radial Target Gauge shows the expected count radius \(R = DPI \times inch\); Path Trace remains an engineering view.

### Directional Axis (engineering characterization)

Known physical distance + directional straight-line movement + Axis Projection + Raw Input counts.

For an X-direction trial, `primary_counts = |counts_x|`. For Y, `primary_counts = |counts_y|`.
Lateral motion is **not** included in the formal directional CPI numerator; it is characterized separately via axis leakage and Path Quality / straightness.

Admission is fail-closed for Axis Projection: selected direction must match signed primary Raw Input movement (Windows relative Y is positive downward, so `Y+` expects `counts_y < 0`).

Typical operator flow:

1. Enter **configured DPI**.
2. Enter the known **physical travel distance** (and unit).
3. Select **geometry** (Fixture Vector or Directional Axis). For Axis mode, select direction `X+` / `X-` / `Y+` / `Y-`.
4. Mark the same physical distance on the test surface / guide.
5. Start Capture.
6. Move the mouse as straight as practical through the **full marked physical distance**.
7. Stop Capture.
8. Review capture integrity / Path Quality / Radial Gauge (Fixture Vector) evidence.
9. Admit a **valid complete** capture as a trial (F5 admits + starts next).
10. Repeat for repeatability analysis.

Important:

- The physical marked travel distance is the measurement ground truth.
- On-screen START→TARGET guidance (Axis mode) is **direction-only**; do not treat screen/cursor travel as the CPI reference.
- Radial Target Gauge is a **target-radius** instrument, not a “draw a circle” test.
- **Effective CPI is not equivalent to native sensor capability.**

Session trials store the existing canonical pair `axis` (`X`|`Y`) and `direction` (`X+`|`X-`|`Y+`|`Y-`). Under Fixture Vector these fields are non-authoritative placeholders (`X` / `X+`); grouping still includes `movement_mode`. **Per-trial `axis` + `direction` are authoritative only for Axis Projection.** Top-level `measurement_context.direction` is non-authoritative.

## Positioning (do not overclaim)

> Mouse DPI Tool is a native Windows Raw Input application for repeatable, evidence-based Effective CPI validation and engineering characterization.

Differentiation is methodology and evidence (native Raw Input, per-device counts, capture integrity, multi-trial repeatability/CV, groups, ratios, Path Quality, Session evidence, Findings, offline desktop workflow)—not marketing claims such as “100% accurate”, “proves native sensor DPI”, or “better than browser DPI analyzers” without controlled benchmarks.

## Quick Start (Windows)

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,ui]"
```

Then either:

- Double-click / run `RUN_Mouse_DPI_Tool.cmd` (prefers `.venv\Scripts\python.exe` when present; same entry as `python -m mouse_dpi_tool ui`)
- Or: `.\.venv\Scripts\mouse-dpi-tool.exe ui`

The launcher does **not** auto-install packages. Prefer the documented `.venv` path. If a system Python launcher is selected and the package is missing, the script prints setup instructions and exits non-zero — create/install `.venv` as above, then re-run.

```powershell
pytest
```

## Packaged Windows UI (onedir) — optional / not required for lab work

**Prefer the Quick Start entry for daily testing.** The packaged EXE + Raw Input helper
is still hardening. Do not treat `dist/MouseDPI_Tool_UI` as Release-ready; keep packaging
sources but use the Python entrypoint until packaging smoke is green.

Build both the main UI and the dedicated Raw Input helper when you need a portable folder:

```powershell
python packaging/build_windows.py
```

Expected layout (keep the **entire folder** together when copying/zipping):

```
dist/MouseDPI_Tool_UI/
  MouseDPI_Tool_UI.exe
  MouseDPI_RawInputBridge.exe
  _internal/...
```

- Start Capture must launch **one** helper process — never a second UI window.
- Packaged helper smoke (optional): `$env:MOUSEDPI_PACKAGED_SMOKE=1; pytest -m windows_hw tests/unit/test_ui1b2_packaged_runtime.py -q`

## Presentation preferences

- **Theme:** Light · Dark · Follow system (OS color scheme via Qt)
- **Locales (architecture):** `en-US`, `zh-TW`, `zh-CN`, `ja-JP`, `ko-KR`, `de-DE`, `fr-FR`, `es-ES`
- Core shell strings are tracked for completeness; catalogs are improving but should not yet be described as “full 8-language localization”
- Domain/schema codes (`PASS`, `ACCURACY_FAIL`, `mm`, `X+`, observation IDs, …) stay English/canonical in Session JSON

## Regenerating golden fixtures (rare)

```powershell
python tools\_generate_legacy_golden_fixtures.py --legacy-root <path-to-MouseDPI_v0.4.1>
```

Legacy golden reference (immutable): `--legacy-root` / `MOUSEDPI_LEGACY_ROOT`
