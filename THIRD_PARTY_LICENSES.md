# Third-Party Licenses

Inventory of dependencies relevant to **source distribution** of Mouse DPI Tool.  
This is not legal advice. Portable binary redistribution of Qt/PySide6 is a **separate** gate.

First-party project code is licensed under MIT — see root `LICENSE`. Third-party components retain their own licenses below.

---

## Runtime (declared)

| Package | Constraint | Role | License (as commonly declared on PyPI) | Bundled in Git tree? | Notes |
|---|---|---|---|---|---|
| jsonschema | `>=4.21` | Session schema validation | MIT (verify pinned wheel METADATA) | No (pip) | Required |
| PySide6 | `>=6.6` (extra `ui`) | Qt UI bindings | LGPL-3.0-only **or** GPL-2.0-only **or** GPL-3.0-only; commercial option via Qt | No | Source install only for first public baseline |
| Shiboken6 | via PySide6 | Binding support | With PySide6 | No | |

### PySide6 / Qt — source vs portable

| Scope | Policy |
|---|---|
| Source-only GitHub | Dependency allowed; document provenance; users install via pip |
| Portable `dist/` binary | **Not** included in first Git baseline; redistribution requires NOTICE, attribution, and LGPL/GPL/commercial compliance review |

Do **not** assume `pip install` equals redistribution compliance for onedir bundles.

---

## Development / test

| Package | Constraint | Role | License (typical) | In portable? |
|---|---|---|---|---|
| pytest | `>=8.0` | tests | MIT | No |

---

## Build (not declared in `pyproject.toml`, used by packaging scripts)

| Package | Role | Notes |
|---|---|---|
| PyInstaller | Windows onedir packaging | Bootloader / license notices required if redistributing binaries |
| setuptools / wheel | build backend | Standard packaging |

---

## Transitive

Transitive licenses follow the resolved environment. Before any **binary** release, freeze a lock or wheel METADATA dump and append notices to this file or a generated `NOTICE`.

---

## Attribution requirements (summary)

1. Keep this file updated when adding dependencies.  
2. For portable builds: ship Qt/PySide notices + offer compliance path for LGPL as applicable.  
3. Do not relicense third-party code as MIT.
