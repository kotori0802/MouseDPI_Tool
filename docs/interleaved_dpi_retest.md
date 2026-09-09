# Fixture Vector procedure + interleaved retest (methodology only)

Not an Experiment Runner. Do **not** mix contaminated and corrected-procedure Trials in one Session.

## Canonical Fixture Vector procedure (preload BEFORE Start)

1. Select configured DPI.
2. Place the carriage at the marked physical start position.
3. **Before** F5 / Start: preload/seat the carriage against the chosen mechanical reference edge.
4. Keep the same preload/reference-edge contact throughout travel.
5. Press F5 / Start.
6. Move **only** along the intended fixture travel to the physical end mark.
7. Do **not** perform lateral seating/re-centering after Capture starts.
8. Stop at the marked physical end position.
9. Press F5 / Stop.
10. Review Integrity / Path Quality / CPI, then Admit.

Suggested DUT Notes (existing metadata — no new schema field):

`Fixture procedure: carriage preloaded against reference edge before Capture.`

### Contaminated capture (do not reuse)

If the operator seats/preloads **after** Start, lateral motion enters Raw Input dx/dy and can inflate Vector Magnitude / make CPI look closer to configured DPI. Treat that Session as contaminated for sensor-only interpretation.

**After correcting procedure: start a NEW Test Session.** Do not append corrected Trials into the old Session.

## Physical distance vs visualizations

- Physical marked travel distance = **ground truth**
- Radial Gauge = visualization / guidance
- Path Trace = engineering visualization

A visually non-straight Path Trace may indicate operator/fixture motion variation even when Accuracy or Path Quality PASS. Accuracy PASS does **not** certify a mechanically ideal path. Path Quality PASS does **not** certify perfect fixture straightness — only that no V1 reversal/jitter rule fired.

## Interleaved clean retest (new Session)

Use interleaved DPI rather than grouped-by-time execution. Target ≥5 clean Trials per DPI.

| Round | Order |
|------|--------|
| 1 | 400 → 1600 → 800 → 3200 |
| 2 | 800 → 3200 → 400 → 1600 |
| 3 | 1600 → 400 → 3200 → 800 |
| 4 | 3200 → 800 → 1600 → 400 |
| 5 | repeat a balanced order |

Before **every** Trial: select DPI → seat against the **same** reference edge → place at start mark → maintain preload → Start → full physical distance → Stop → Admit.

Do not intentionally include post-Start seating in the clean reference Session.

## Optional engineering A/B (separate Sessions; not automated in V1)

| Condition | Procedure |
|-----------|-----------|
| A | Carriage allowed lateral play (no consistent preload) |
| B | Consistent mechanical preload against one reference edge **before** Capture |

Compare descriptively: Effective CPI group means, max Trial error, CV, ratio behavior, Path Quality, **axial** orientation spread. Future V1.5 may add cross-track residuals. Do not automate in V1.

## How to read clean interleaved results

Allowed:

- measured group means remain below configured CPI
- bias pattern differs from a prior grouped-run Session
- one DPI shows highest dispersion
- adjacent ratios WARN
- fixture/operator confound remains possible if procedure was mixed

Not allowed as V1 conclusions:

- sensor is defective
- interpolation / firmware scaling proven
- fixture is crooked based on CPI alone

## Reference note (methodology only — not production thresholds)

A prior ~25-Trial interleaved Session (mixed/possibly contaminated seating) is preserved only as a methodology example. Do not special-case those numeric values in production logic. Re-run under corrected procedure in a **new** Session before treating data as clean sensor-only behavior.

## Pre/post preload methodology comparison (descriptive)

| | Mixed / inconsistent preload Session (approx.) | Corrected preload-before-Start Session (approx.) |
|--|-----------------------------------------------|--------------------------------------------------|
| Max Trial error | up to ~8.98% | ~4.23% |
| Max CPI CV | ~3.03% | ~1.02% |
| Adjacent ratio pairs | all WARN (~±3%) | all PASS (max \|ratio error\| ~0.42%) |

Allowed: *Standardizing fixture preload materially reduced observed measurement variation in this experiment.*  
Not allowed: *All previous errors were caused by fixture preload.*

## Physical distance calibration (engineering note)

Configured physical distance must correspond to the actual **sensor** displacement between the chosen physical start and end references.

Do **not** measure merely fixture outer width, opening size, or carriage shell edge if those do not match sensor travel.

Verify start-to-end displacement with an independent physical reference before drawing sensor conclusions. No specific instrument brand is required. No automatic distance correction in V1.

## Absolute Accuracy vs Relative DPI Scaling

- **Accuracy** = absolute Effective CPI vs configured DPI  
- **Relative DPI Scaling** (Finding key still `ratio`) = measured step ratio vs configured step ratio  

A Session may show a near-common absolute scale offset (e.g. all group means ~2.6–3.3% low) while adjacent measured ratios stay within ~0.4% of configured ratios. These describe different properties. Do **not** claim interpolation absent, sensor linearity proven, or native capability proven.

**Cross-DPI Scale Pattern** (Results / report descriptive helper) summarizes group-mean scale factors. It is **not** a Finding and does **not** assign root cause (distance, fixture, product CPI offset, etc.).
