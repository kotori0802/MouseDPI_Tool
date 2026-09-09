# Software validation summary

Mouse DPI Tool ships with automated regression coverage for core measurement and
capture behavior. Before the public source baseline, a physical operator workflow
check was performed on a local engineering setup.

## What is covered

- Capture lifecycle and integrity behavior (start / stop / admit / discard paths)
- Measurement calculations, Findings classification, and Session ↔ HTML report consistency
- Synthetic regression fixtures for numerical parity with the owner’s earlier prototype tooling
- Public `examples/` Session and HTML report data that is **synthetic** only

## What is not distributed

Private physical qualification Sessions, HTML reports, screenshots, and development
gate records are intentionally **not** included in the public repository.

Public example data uses fictional identifiers (for example ExampleVendor / DemoMouse)
and states:

> Synthetic demonstration data — not a real product validation result.

## Positioning

Validation here means: the Tool records, computes, and reports evidence according to
its published contracts. It does **not** mean every device under test (DUT) must measure
exactly at configured DPI. Accuracy / repeatability WARN or FAIL Findings can be valid
measurement outcomes.
