# Motion timing + surface / direction methodology (MS-1 / UI-3A.5)

Auxiliary engineering evidence only. **No speed correction of CPI.**

## Timing definition

`active_motion_duration_ms` = span from the first accepted Raw Input movement sample
timestamp to the last movement sample timestamp for one Capture.

Preferred source: `MovementSample.timestamp_s` from the Raw Input bridge
(`time_perf` = `time.perf_counter()`).

Fallback: capture-boundary monotonic clock when sample timestamps are missing.

`estimated_traversal_speed_mm_s` = `distance_mm / active_motion_duration_s`.

Wording: **Estimated traversal speed** — not true physical speed.

Never: `speed = event_count` or `counts / event_count`.

## Tracking surface vs fixture contact

| Concept | Meaning |
|---------|---------|
| Tracking surface | Material directly observed by the optical sensor |
| Fixture / carriage contact | Material / friction / preload of the mechanical fixture |

Do not claim these are the same mechanism. No `SURFACE_FAIL` / `FIXTURE_MATERIAL_FAIL` Findings in V1.

## Controlled experiments

### Speed-only (same everything else)

same DUT · same DPI · same 50.8 mm travel · same tracking surface · same preload ·
balanced forward/reverse · change **only** traversal speed.

Classify speed from measured `active_motion_duration`, not operator guesses.

### Surface-only

Separate Sessions; change **only** tracking surface. Do not merge surfaces into one
quantitative group unless measurement_context explicitly supports comparison.

## Schema

`trial.motion_timing` is **optional**. Historical Sessions without it remain valid.
Schema version stays `MOUSE_DPI_TOOL_SESSION_V1`.

## 90-Trial reference interpretation (methodology only)

A large interleaved Fixture Vector soak can show:

- all four DPI group means below configured DPI (~−2.6% to −3.5% group-average)
- CPI CV roughly 1.2–1.6%
- Relative DPI Scaling pairs PASS (max |ratio error| < 1%)
- Accuracy FAIL driven by individual Trial tails (>5%), not a 7% mean offset
- rare Path Quality FAIL must not explain the Accuracy pattern
- without stored timing evidence, speed dependence is **not** concluded

Do not hardcode these values into production logic.
