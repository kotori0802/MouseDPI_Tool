"""Localization catalogs — display strings only; never written into Session evidence."""

from __future__ import annotations

# Stable keys → English (canonical fallback). Other locales override as available.
_EN: dict[str, str] = {
    "app.title": "Mouse DPI Tool",
    "nav.setup": "Setup",
    "nav.capture": "Capture",
    "nav.results": "Results",
    "nav.settings": "Settings",
    "setup.title": "Session setup",
    "setup.subtitle": "DUT and measurement configuration for this session.",
    "setup.dut": "Device under test",
    "setup.vendor": "Vendor",
    "setup.model": "Model",
    "setup.notes": "Notes",
    "setup.notes_deviations": "Notes / deviations",
    "setup.revert": "Revert changes",
    "setup.apply_failed": "Could not apply setup changes.",
    "setup.surface": "Tracking surface",
    "setup.surface_hint": "Surface directly observed by the mouse sensor (not fixture carriage material).",
    "setup.fixture_type": "Fixture / contact notes",
    "setup.method": "Fixture / test method",
    "setup.method_recovered": (
        "Saved Method was not a supported value. Select a Method from the list and Apply."
    ),
    "setup.ctx_notes": "Engineering notes",
    "setup.dpi_configuration_source": "DPI configuration source",
    "setup.dpi_source.hardware_control": "Hardware control",
    "setup.dpi_source.onboard_profile": "Onboard profile",
    "setup.dpi_source.vendor_software": "Vendor software",
    "setup.dpi_source.other": "Other",
    "setup.dpi_source.unknown": "Unknown",
    "setup.control_software_state": "Control software state",
    "setup.control_state.not_running": "Not running",
    "setup.control_state.ui_open": "UI open",
    "setup.control_state.background_service_present": "Background service present",
    "setup.control_state.unknown": "Unknown",
    "setup.control_software_name": "Control software name",
    "setup.control_software_version": "Control software version",
    "setup.profile_note": "Profile note",
    "setup.measurement_system_uncertainty_note": "Measurement-system uncertainty note",
    "setup.reference_uncertainty_pct": "Reference uncertainty (%)",
    "setup.reference_uncertainty_unset": "—",
    "setup.distance": "Physical distance",
    "setup.unit": "Unit",
    "setup.apply": "Apply",
    "setup.applied": "Applied. Testing will use {distance} {unit} for this session.",
    "setup.applied_with_mm": (
        "Applied. Testing will use {distance} {unit} (= {mm} mm physical) for this session."
    ),
    "setup.physical_mm_preview": "= {mm} mm used for CPI",
    "setup.unit_keep_number_help": (
        "Changing Unit keeps the number you typed and reinterprets it. "
        "Example: type 2, then choose inches → 2 in (= 50.8 mm). "
        "It does not auto-convert the previous unit's length."
    ),
    "setup.unit_keep_number_hint": (
        "Unit set to {unit}; number kept as {value}. "
        "Check physical mm above, then Apply."
    ),
    "setup.optional_meta": "Optional session notes (not required for measurement)",
    "setup.group.dut": "DUT identity",
    "setup.group.measurement": "Measurement configuration",
    "setup.group.notes": "Optional notes",
    "setup.meta.fixture_env": "Fixture / environment",
    "setup.meta.dpi_config": "DPI configuration",
    "setup.meta.uncertainty": "Measurement uncertainty",
    "setup.movement_mode": "Movement mode",
    "setup.geometry": "Measurement geometry",
    "setup.accuracy": "Accuracy criterion",
    "setup.accuracy.strict": "Strict (3%)",
    "setup.accuracy.medium": "Medium (6%)",
    "setup.accuracy.lenient": "Lenient (9%)",
    "setup.accuracy.help.FIELD_STRICT": "PASS ≤ 3% · WARN 3–5% · FAIL > 5%",
    "setup.accuracy.help.FIELD_MEDIUM": "PASS ≤ 6% · WARN 6–8% · FAIL > 8%",
    "setup.accuracy.help.FIELD_LENIENT": "PASS ≤ 9% · WARN 9–11% · FAIL > 11%",
    "setup.accuracy_locked": (
        "Acceptance criteria are locked after measurement evidence is created."
    ),
    "trials.tab.active": "Active",
    "trials.tab.rejected": "Rejected",
    "trials.tab.deleted": "History",
    "trials.reject": "Reject",
    "trials.restore": "Restore",
    "trials.delete": "Move to history",
    "trials.new_session": "New test Session",
    "trials.new_session_confirm": (
        "Start a new test Session? Current Trial evidence stays in memory only until export "
        "and will not carry into the new Session."
    ),
    "trials.new_session_done": "New test Session ready. Accuracy criterion is editable again.",
    "trials.select_one": "Select a Trial first.",
    "trials.summary": (
        "Active {active} · Rejected {rejected} · History {deleted} · DPI groups: {groups} · "
        "Accuracy: {criterion} ({bands})"
    ),
    "trials.filter.all_dpi": "All DPI",
    "trials.filter.dpi": "DPI:",
    "trials.sort.label": "Sort:",
    "trials.sort.newest": "Newest Trial",
    "trials.sort.oldest": "Oldest Trial",
    "trials.sort.dpi_asc": "DPI low → high",
    "trials.sort.dpi_desc": "DPI high → low",
    "trials.sort.abs_error": "Largest absolute error",
    "trials.sort.status": "Status severity",
    "trials.col.id": "Trial #",
    "trials.col.id_desc": "Trial # ↓",
    "trials.col.id_asc": "Trial # ↑",
    "trials.col.dpi": "Configured DPI",
    "trials.col.geometry": "Geometry",
    "trials.col.distance": "Distance",
    "trials.col.cpi": "Measured CPI",
    "trials.col.error": "Error %",
    "trials.col.status": "Status",
    "trials.col.path_quality": "Path Quality",
    "trials.col.direction": "Direction",
    "geometry.fixture_vector": "Fixture Vector (any-angle straight line)",
    "geometry.directional_axis": "Directional Axis (X+/X-/Y+/Y−)",
    "geometry.tile.fixture_sub": "Any-angle straight travel · Vector Magnitude",
    "geometry.tile.axis_sub": "Axis-constrained travel · choose direction on Capture",
    "setup.measurement_locked": (
        "Measurement distance is locked while a capture is active or pending. "
        "Admit, Cancel, or discard that capture before changing geometry."
    ),
    "capture.title": "Capture",
    "capture.subtitle": "Raw Input capture controls. Engineering evidence stays in the domain layer.",
    "capture.start": "Start",
    "capture.admit_and_start": "Admit + Start next",
    "capture.stop": "Stop",
    "capture.cancel": "Cancel",
    "capture.admit": "Admit trial",
    "capture.discard": "Discard failed run",
    "capture.discarded": "Failed/pending capture discarded. Measurement settings unlocked.",
    "capture.configured_dpi": "Configured DPI",
    "capture.configured_dpi_hint": (
        "Operator-entered DUT setting (not auto-read from the mouse)."
    ),
    "capture.dpi_confirmation_recommended": "DUT DPI confirmation recommended",
    "capture.ready_move_now": "READY — MOVE NOW",
    "capture.ready_move_hint": (
        "Move only after READY. Radial Gauge returning to center is presentation only — "
        "not the capture-ready signal."
    ),
    "capture.geometry": "Geometry",
    "capture.geometry_readonly_hint": "Committed in Setup — change geometry there, then Apply.",
    "capture.action.starting": "Starting…",
    "capture.action.processing": "Processing…",
    "capture.help.idle": "Set Configured DPI, confirm geometry above, then Start (F5).",
    "capture.help.arming": "Arming capture — wait for Ready before moving.",
    "capture.help.running": "Move the mouse along the planned path, then Stop (F5) or Cancel (Esc).",
    "capture.help.stopping": "Finishing capture — please wait.",
    "capture.help.review": "Review the result, then Admit & Start next (F5) or Discard.",
    "capture.help.discard_only": "This capture cannot be admitted — Discard and retry.",
    "capture.direction": "Direction",
    "capture.physical_distance": "Physical distance",
    "capture.path_trace": "Path Trace (engineering view)",
    "capture.instruction": (
        "Move the mouse through the full pre-marked physical distance. "
        "The on-screen guide is only for direction guidance; do not try to align "
        "the mouse/cursor with the target marker."
    ),
    "capture.instruction_fixture": (
        "Before Start, seat the carriage against the reference edge at the physical start mark. "
        "After Start, move only along the intended fixture travel — do not re-seat or re-center. "
        "Aim for the target radius on the Radial Gauge; Path Trace is engineering review only. "
        "Physical marked distance is ground truth."
    ),
    "capture.procedure_hint": (
        "Before Start, seat the carriage against the reference edge at the physical "
        "start mark. Do not re-seat or re-center after capture begins."
    ),
    "capture.lane.start": "START",
    "capture.lane.target": "TARGET",
    "direction.X+": "X+ · Left → Right",
    "direction.X-": "X- · Right → Left",
    "direction.Y+": "Y+ · Bottom → Top",
    "direction.Y-": "Y- · Top → Bottom",
    "capture.state": "State",
    "capture.status": "Status",
    "capture.nets": "Net counts",
    "capture.events": "events",
    "capture.devices": "devices",
    "capture.ready_to_admit": (
        "Valid capture ready — not in the trial table yet. "
        "F5 / Start = admit + next; Admit = add only. "
        "Change DPI to discard this run without admitting."
    ),
    "capture.discarded_for_dpi": "Pending capture discarded so DPI can change.",
    "capture.admitted": "Admitted trial {trial_id}.",
    "capture.admitted_next": "Admitted trial {trial_id}. Starting next capture…",
    "capture.mismatch": "Selected: {selected} · Observed movement: {observed}",
    "capture.zero_primary": "No primary-axis movement for the selected direction.",
    "capture.focus_lost": (
        "Capture was cancelled because the application lost focus. Repeat the measurement."
    ),
    "capture.runtime_diag": "Runtime",
    "capture.display.idle": "Ready",
    "capture.display.starting": "Starting",
    "capture.display.capturing": "Capturing",
    "capture.display.stopping": "Stopping",
    "capture.display.cancelling": "Cancelling",
    "capture.display.discarding": "Discarding",
    "capture.display.valid_stopped": "Valid capture",
    "capture.display.direction_mismatch": "Direction mismatch",
    "capture.display.zero_primary": "No primary movement",
    "capture.display.cancelled": "Cancelled",
    "capture.display.error": "Error / incomplete",
    "capture.display.stopped": "Stopped",
    "capture.path_quality": "Path Quality",
    "capture.primary_counts": "Primary counts",
    "capture.integrity": "Integrity",
    "capture.integrity_pending": "Pending (finalizes on Stop)",
    "capture.integrity_na": "N/A",
    "capture.live_provisional": "live / provisional",
    "capture.tech_details": "Technical details",
    "capture.nav_locked": "Stay on Capture while a measurement is active.",
    "capture.poster.empty_title": "Latest trial",
    "capture.poster.empty_body": "No captured trial yet",
    "capture.poster.pending": (
        "Pending admit — not in table yet (F5 = admit + next; change DPI = discard)"
    ),
    "capture.poster.admitted": "Trial {trial_id} admitted",
    "capture.poster.last_admitted": "Last admitted Trial {trial_id}",
    "capture.poster.error": "Error {error}%",
    "capture.poster.meta": (
        "Configured {configured} DPI · error {error}% · dx={dx} dy={dy} · "
        "primary={primary} · {mode} · {direction}"
    ),
    "capture.poster.vector_ref": (
        "Vector Magnitude reference (diagonal fixture): {vector_cpi} CPI — "
        "switch Geometry to Fixture Vector for official √(dx²+dy²) CPI."
    ),
    "capture.poster.fixture_hint": (
        "Fixture Vector: official CPI uses √(dx²+dy²) / inch against the known distance."
    ),
    "results.title": "Results",
    "results.subtitle": "Human-facing Findings from active quantitative evidence.",
    "results.summary": "Active trials: {trials} · Groups: {groups} · Relative DPI Scaling pairs: {ratios}",
    "results.empty_title": "No measurement results yet.",
    "results.empty_body": (
        "Complete a measurement Trial to begin building engineering evidence."
    ),
    "results.empty_go_capture": "Go to Capture",
    "results.empty_open_guide": "Open User Guide",
    "results.trials": "Active trials",
    "results.groups": "Groups",
    "results.ratios": "Relative DPI Scaling",
    "results.research": "Research / Not Evaluated",
    "results.groups_title": "DPI Group Summary",
    "results.ratios_title": "Relative DPI Scaling",
    "results.ratios_hint": (
        "Compares measured CPI step ratios with configured ratios — relative scaling, "
        "not absolute CPI closeness."
    ),
    "results.scale_pattern_title": "Cross-DPI Scale Pattern",
    "results.findings_title": "Measurement Findings",
    "results.evidence_title": "DPI Evidence Summary",
    "results.eng_diag_title": "Advanced / Engineering Diagnostics",
    "results.eng_diag_collapsed_hint": (
        "Trial sequence, CPI distributions, estimated speed association, and "
        "ready-to-first-motion diagnostics."
    ),
    "results.eng_diag_hint": (
        "Descriptive Trial distribution views from canonical evidence — not Findings. "
        "Estimated traversal speed is not true physical speed."
    ),
    "results.trial_sequence_title": "Trial CPI Error over Test Sequence",
    "results.trial_dist_title": "CPI Error Distribution by DPI",
    "results.speed_error_title": "CPI Error vs Estimated Traversal Speed",
    "results.speed_unavailable": "Motion timing evidence not available for this Session.",
    "results.speed_corr_wording": (
        "Some DPI groups show within-group association between estimated traversal "
        "speed and CPI error; direction and strength are not consistent across all "
        "DPI groups. Not a causal Finding. event_count is not speed."
    ),
    "results.latency_error_title": "CPI Error vs Ready-to-First-Motion Delay",
    "results.latency_error_hint": (
        "Descriptive only — whether Trials that move sooner after READY differ from "
        "Trials with longer operator dwell. No PASS/WARN/FAIL; no minimum safe delay invented."
    ),
    "results.dpi_filter": "DPI filter",
    "results.dpi_filter_all": "All DPI",
    "results.trends_title": "DPI Behavior Trends",
    "results.trends_hint": (
        "Descriptive charts from canonical group summaries — not a Finding and not a "
        "high-DPI interpolation verdict."
    ),
    "results.group.dpi": "Configured DPI",
    "results.group.trials": "Trials",
    "results.group.avg_cpi": "Avg measured CPI",
    "results.group.max_error": "Max |error| %",
    "results.group.cv": "CPI CV %",
    "results.group.status": "Status",
    "results.ratio.from": "From DPI",
    "results.ratio.to": "To DPI",
    "results.ratio.expected": "Configured ratio",
    "results.ratio.measured": "Measured ratio",
    "results.ratio.error": "Ratio error %",
    "results.ratio.status": "Status",
    "results.report.generate": "Generate Report…",
    "results.report.choose_folder": "Choose report destination folder",
    "results.report.busy": "Generating report…",
    "results.report.done": "Report written to {folder}:\n{html}\n{json}",
    "results.report.failed": "Report failed: {error}",
    "results.report.method_invalid": (
        "Method metadata is invalid. Select a supported Method before export."
    ),
    "charts.measured_cpi.title": "Measured CPI vs Configured DPI",
    "charts.measured_cpi.caption": (
        "Compare each DPI group's average measured CPI to the ideal 1:1 target; "
        "closer to the ideal line means Effective CPI is nearer the configured value."
    ),
    "charts.max_error.title": "Maximum CPI error by DPI",
    "charts.max_error.caption": (
        "Maximum absolute CPI error per DPI group, compared with this Session's "
        "Accuracy PASS / WARN / FAIL thresholds."
    ),
    "charts.repeatability.title": "Repeatability (CPI CV)",
    "charts.repeatability.caption": (
        "CPI CV is the dispersion of repeated measurements at the same DPI; "
        "lower values mean higher repeatability."
    ),
    "charts.obs.cpi.all_below_ideal": (
        "All measured group means are below the ideal 1:1 reference; "
        "the largest group error is {max_abs_error_pct}%."
    ),
    "charts.obs.cpi.all_above_ideal": (
        "All measured group means are above the ideal 1:1 reference; "
        "the largest group error is {max_abs_error_pct}%."
    ),
    "charts.obs.cpi.mixed_vs_ideal": (
        "Measured group means sit both above and below the ideal 1:1 reference; "
        "the largest group error is {max_abs_error_pct}%."
    ),
    "charts.obs.cpi.no_data": "No DPI group averages are available for this Session.",
    "charts.obs.error.band_counts": (
        "PASS {pass} · WARN {warn} · FAIL {fail} DPI groups by maximum absolute CPI error "
        "vs Session Accuracy thresholds (PASS ≤ {pass_pct:g}% · WARN > {pass_pct:g}%–"
        "{fail_pct:g}% · FAIL > {fail_pct:g}%)."
    ),
    "charts.obs.error.no_data": "No DPI group error values are available for this Session.",
    "charts.obs.cv.highest": "{dpi} DPI has the highest CPI CV in this Session ({cv}%).",
    "charts.obs.cv.no_data": "No DPI group CPI CV values are available for this Session.",

    "capture.start_f5": "Start  F5",
    "capture.stop_f5": "Stop  F5",
    "capture.cancel_esc": "Cancel  Esc",
    "capture.admit_and_start_f5": "Admit + Start next  F5",
    "capture.shortcut_hint": "Shortcuts: F5 Start / Stop · Esc Cancel",
    "capture.how_to_measure": "? How to measure",
    "capture.how_to_measure_body": (
        "<ol>"
        "<li>Select configured DPI.</li>"
        "<li>Place the carriage at the marked physical start position.</li>"
        "<li><b>Before</b> F5 / Start: preload/seat the carriage against the chosen "
        "mechanical reference edge; keep that contact throughout travel.</li>"
        "<li>Press F5 / Start.</li>"
        "<li>Move only along the intended fixture travel to the physical end mark "
        "(do not lateral seat / re-center after Start).</li>"
        "<li>Stop at the marked end; press F5 / Stop.</li>"
        "<li>Review Integrity / Path Quality / CPI, then Admit.</li>"
        "</ol>"
        "<p>Physical marked travel distance is ground truth. Radial Gauge = visualization/guidance; "
        "Path Trace = engineering visualization. A non-straight Path Trace may indicate operator/"
        "fixture motion variation even when Accuracy or Path Quality PASS. "
        "Accuracy PASS does not certify a mechanically ideal path. "
        "Path Quality PASS does not certify perfect fixture straightness. "
        "F5/Esc are shortcuts, not required.</p>"
    ),
    "capture.dpi_presets": "Presets",
    "capture.dpi_spin_tip": "Configured DPI (source of truth)",
    "capture.dpi_preset_tip": "Jump to a common configured DPI preset",
    "setup.accuracy_locked_short": "Locked",
    "help.guide.title": "User Guide",
    "help.guide.open": "? User Guide",
    "help.section.quick_start": "A. Quick Start",
    "help.body.quick_start": (
        "Configure DPI and distance → Capture → seat carriage against the reference edge "
        "at the physical start mark <b>before</b> F5 Start → move only along the fixture travel → "
        "F5 Stop → review → Admit. Do not re-seat after Start. Physical distance is ground truth. "
        "After correcting procedure, start a <b>new</b> Test Session — do not mix old and corrected Trials."
    ),
    "help.section.shortcuts": "B. Keyboard Shortcuts",
    "help.body.shortcuts": "F5 Start / Stop · Esc Cancel. Hints also appear on Capture buttons.",
    "help.section.methods": "C. Measurement Methods",
    "help.body.methods": (
        "<b>Fixture Vector</b>: arbitrary-angle straight line; CPI uses vector magnitude.<br/>"
        "<b>Directional Axis</b>: X+/X-/Y+/Y−; CPI uses axis projection."
    ),
    "help.section.findings": "D. Understanding Findings",
    "help.body.findings": (
        "Accuracy: how close Effective CPI is to configured DPI (absolute).<br/>"
        "Repeatability: consistency within a DPI group (lower CV is better).<br/>"
        "Relative DPI Scaling: compares measured CPI ratios between DPI steps with "
        "configured ratios — useful for relative-scaling review; does not prove "
        "sensor linearity or native capability.<br/>"
        "Path Quality: no V1 reversal/jitter path anomaly when PASS — "
        "not tracking/sensor/native capability, and not perfect fixture straightness. "
        "WARN with incomplete coverage means some Trials lacked evaluable path evidence "
        "(not necessarily a path failure)."
    ),
    "help.section.trends": "E. Understanding DPI Behavior Trends",
    "help.body.trends": (
        "Chart 1: closer to the ideal 1:1 line is better.<br/>"
        "Chart 2: lower error is better; PASS/WARN/FAIL follow Session thresholds.<br/>"
        "Chart 3: lower CPI CV means better repeatability."
    ),
    "help.section.criterion": "F. Acceptance Criterion",
    "help.body.criterion": (
        "Strict / Medium / Lenient set PASS and FAIL CPI-error limits (WARN is the band between). "
        "Locked after measurement evidence exists."
    ),
    "help.section.limits": "G. Method Limitations",
    "help.body.limits": (
        "This tool validates Effective CPI against a known physical distance using native Windows Raw Input. "
        "It does not prove native sensor resolution and does not conclude firmware interpolation/scaling in V1. "
        "Configured physical distance must match the actual sensor displacement between the chosen "
        "start and end references — not merely fixture outer width, opening size, or carriage shell edge "
        "if those differ from sensor travel. Verify start-to-end displacement with an independent "
        "physical reference before drawing sensor conclusions. "
        "Tracking surface (material seen by the optical sensor) is distinct from fixture/carriage "
        "contact condition (material / friction / preload). Do not treat them as the same mechanism."
    ),
    "finding.metric.max_individual_error": "Maximum individual CPI error",
    "finding.metric.pq_not_evaluated": "NOT_EVALUATED",
    "finding.metric.pq_coverage_note": "Coverage note",
    "finding.metric.pq_coverage_value": (
        "WARN reflects incomplete path-evidence coverage "
        "({n} NOT_EVALUATED); no PQ FAIL detected."
    ),
    "finding.metric.groups_dist": "Groups",
    "finding.metric.active_trials": "Active Trials",
    "finding.metric.max_cpi_cv": "Maximum CPI CV",
    "finding.metric.min_trials": "Min trials / group",
    "finding.metric.max_ratio_error": "Maximum |ratio error|",
    "finding.metric.pairs_dist": "Pairs",
    "finding.metric.pq_pass": "Path Quality PASS",
    "finding.metric.pq_warn": "WARN",
    "finding.metric.pq_fail": "FAIL",
    "finding.metric.pq_trials": "Trials with PQ",
    "finding.help.accuracy": "How close measured Effective CPI is to configured DPI.",
    "finding.help.repeatability": "How consistent repeated measurements are within the same DPI group.",
    "finding.help.ratio": (
        "Compares measured CPI ratios between DPI steps with their configured ratios. "
        "Useful for relative-scaling review; it does not prove sensor linearity or "
        "native capability."
    ),
    "finding.help.path_quality": (
        "No path-quality issue defined by the current V1 reversal/jitter rules was detected when PASS. "
        "Does not mean perfect physical fixture straightness or zero lateral motion. "
        "WARN with incomplete coverage means one or more Trials lacked evaluable path evidence "
        "(e.g. NOT_EVALUATED) — not that a path failure was detected. "
        "Not Tracking / Sensor / Native capability."
    ),
    "finding.help.research": "Reserved for future characterization; V1 does not infer these properties from Raw Input alone.",
    "charts.how_to_read": "How to read this chart",
    "charts.measured_cpi.legend": "Measured average · Ideal 1:1",
    "charts.max_error.legend": "Max individual |error| % · PASS / WARN / FAIL thresholds",
    "charts.repeatability.legend": "CPI CV % · Repeatability PASS / WARN / FAIL thresholds",
    "charts.measured_cpi.cue": "Closer to the grey 1:1 ideal line means Effective CPI is nearer the configured value.",
    "charts.max_error.cue": "Lower is better; PASS / WARN / FAIL bands follow this Session's Accuracy thresholds.",
    "charts.repeatability.cue": "Lower CV means repeated measurements at the same DPI are more consistent.",
    "charts.measured_cpi.x": "Configured DPI",
    "charts.measured_cpi.y": "Average measured CPI",
    "charts.max_error.x": "Configured DPI",
    "charts.max_error.y": "Maximum absolute CPI error (%)",
    "charts.repeatability.x": "Configured DPI",
    "charts.repeatability.y": "CPI CV (%)",
    "charts.measured_cpi.metric_note": (
        "Chart summary uses deviation of group-average CPI from configured DPI. "
        "Accuracy Finding uses maximum individual Trial |error| — different metrics."
    ),
    "charts.max_error.metric_note": "Uses each group's maximum absolute Trial CPI error (same family as Accuracy).",
    "charts.obs.cpi.all_below_ideal": (
        "All measured group means are below the ideal 1:1 reference; "
        "the largest deviation of group-average CPI from configured DPI is {max_mean_deviation_pct}%."
    ),
    "charts.obs.cpi.all_above_ideal": (
        "All measured group means are above the ideal 1:1 reference; "
        "the largest deviation of group-average CPI from configured DPI is {max_mean_deviation_pct}%."
    ),
    "charts.obs.cpi.mixed_vs_ideal": (
        "Measured group means sit both above and below the ideal 1:1 reference; "
        "the largest deviation of group-average CPI from configured DPI is {max_mean_deviation_pct}%."
    ),
    "report.interpretation.title": "How to read this report",
    "report.interpretation.body": (
        "Accuracy: absolute Effective CPI vs configured DPI (maximum individual Trial error).<br/>"
        "Relative DPI Scaling: measured CPI step ratios vs configured step ratios "
        "(relative scaling — not absolute CPI closeness).<br/>"
        "Absolute CPI values may share a common offset while relative DPI-step ratios remain "
        "consistent; these describe different properties.<br/>"
        "Repeatability: consistency within a DPI group (lower CPI CV is better).<br/>"
        "Path Quality: no V1 reversal/jitter anomaly when PASS; incomplete-coverage WARN means "
        "missing evaluable path evidence on some Trials — not necessarily a path failure.<br/>"
        "Cross-DPI Scale Pattern: descriptive group-mean scale factors — not a Finding and not a root cause.<br/>"
        "Measured CPI chart: closer to 1:1 ideal is better (group-average deviation ≠ Accuracy max error).<br/>"
        "Error chart: lower is better; PASS/WARN/FAIL use Session thresholds.<br/>"
        "CV chart: lower means better repeatability."
    ),
    "scale.pattern.title": "Cross-DPI Scale Pattern",
    "scale.pattern.disclaimer": "Descriptive diagnostic only — not a Finding; no automatic root cause.",
    "scale.pattern.none": "Insufficient DPI-group means for a scale pattern.",
    "scale.pattern.groups": "Evaluated DPI groups: {n}",
    "scale.pattern.scale_range": (
        "Normalized scale (avg CPI / configured): {min_s} – {max_s} "
        "(mean {mean_s}, median {med_s}, spread {spread})"
    ),
    "scale.pattern.dev_range": (
        "Group-average deviation from configured: approximately {lo:+.2f}% to {hi:+.2f}%."
    ),
    "scale.pattern.common_with_ratio": (
        "All evaluated DPI-group means share a near-common offset from configured values, "
        "while adjacent measured DPI ratios remain close to their configured ratios "
        "(max |ratio error| {err}%). This warrants measurement-system or product calibration "
        "review — not an automatic fixture or sensor verdict."
    ),
    "scale.pattern.common": (
        "All evaluated DPI-group means share a near-common offset from configured values. "
        "This warrants measurement-system or product calibration review — "
        "not an automatic fixture or sensor verdict."
    ),
    "scale.pattern.mixed": (
        "Scale factors differ materially across DPI groups (or signs mix). "
        "Not described as a common-scale-offset pattern."
    ),
    "scale.pattern.no_root_cause": (
        "Possible contributors include travel-distance definition, fixture geometry/preload, "
        "start/end references, product-wide CPI offset, or other common effects. "
        "The Tool does not choose among them."
    ),

    "fixture.diag.title": "Fixture / Motion Diagnostics",
    "fixture.diag.disclaimer": "Descriptive diagnostics only — no fixture/sensor verdict.",
    "fixture.diag.none": "Fixture / Motion Diagnostics: no Fixture Vector trials.",
    "fixture.diag.avg_straightness": "Average straightness: {value}%",
    "fixture.diag.min_straightness": "Minimum straightness: {value}%",
    "fixture.diag.max_path_excess": "Maximum path excess: {value}%",
    "fixture.diag.mean_heading": "Fixture axis orientation: {value}°",
    "fixture.diag.heading_spread": "Axis-orientation spread: {value}°",
    "fixture.diag.axis_orientation": "Fixture axis orientation: {value}°",
    "fixture.diag.axis_spread": "Axis-orientation spread: {value}°",
    "fixture.diag.axis_note": (
        "Axis orientation is axial (mod 180°). Absolute angle is not a quality score; "
        "opposite travel polarity does not inflate spread."
    ),
    "fixture.diag.polarity": (
        "Travel polarity — forward: {forward} · reverse: {reverse} (descriptive only)."
    ),
    "fixture.diag.avg_straightness_ceiling": "Average straightness: {value}% (metric ceiling)",
    "fixture.diag.min_straightness_ceiling": "Minimum straightness: {value}% (metric ceiling)",
    "fixture.diag.path_excess_ne": "Path excess: NOT_EVALUATED (path_total < vector under noise-floor semantics)",
    "fixture.diag.heading_note": (
        "Axis-orientation spread reflects fixture-axis consistency (mod 180°), not fixture straightness."
    ),
    "fixture.diag.per_dpi_title": "Per-DPI motion consistency (descriptive):",
    "fixture.diag.per_dpi_header": (
        "DPI | Trials | Axis orient. | Axis spread | Fwd/Rev | Avg straightness | Path excess"
    ),
    "fixture.diag.ceiling_footnote": "* straightness at Path Quality metric ceiling (≤100%)",
    "fixture.diag.missing": "Insufficient canonical evidence: {fields}",
    "help.section.fixture_motion": "H. Fixture / Motion Diagnostics",
    "help.body.fixture_motion": (
        "Straight diagonal fixtures are valid. Fixture Vector uses axial (mod 180°) orientation — "
        "θ and θ+180° are the same axis. Look at straightness, path excess, and axis-orientation "
        "spread — never CPI error alone. Descriptive only; not a fixture or sensor PASS/FAIL. "
        "Path Quality PASS means no V1 reversal/jitter rule fired — not perfect physical straightness."
    ),
    "settings.title": "Preferences",
    "settings.subtitle": "Theme and language are presentation preferences — not Session evidence.",
    "settings.theme": "Theme",
    "settings.locale": "Language",
    "theme.light": "Light",
    "theme.dark": "Dark",
    "theme.system": "Follow system",
    "finding.accuracy": "Accuracy",
    "finding.repeatability": "Repeatability",
    "finding.ratio": "Relative DPI Scaling",
    "finding.path_quality": "Path Quality",
    "finding.manual_observations": "Manual observations",
    "finding.linearity": "Linearity",
    "finding.scaling_evidence": "Scaling evidence",
    "finding.native_capability": "Native capability",
    "status.PASS": "Pass",
    "status.WARN": "Warn",
    "status.FAIL": "Fail",
    "status.NOT_TESTED": "Not tested",
    "status.NOT_EVALUATED": "Not evaluated",
    "status.SKIP": "Skip",
    "unit.mm": "millimetres (mm)",
    "unit.cm": "centimetres (cm)",
    "unit.inch": "inches (inch)",
    "method.hand_drag": "Hand drag",
    "method.click_click": "Click-click",
    "method.fixture": "Fixture",
    "method.synthetic": "Synthetic",
    "method.unknown": "Unknown",
    "issue.ACCURACY_WARN": "Accuracy warning",
    "issue.ACCURACY_FAIL": "Accuracy failure",
    "issue.REPEATABILITY_WARN": "Repeatability warning",
    "issue.REPEATABILITY_FAIL": "Repeatability failure",
    "issue.INSUFFICIENT_REPEATABILITY_EVIDENCE": "Insufficient repeatability evidence",
    "issue.RATIO_WARN": "Ratio warning",
    "issue.RATIO_FAIL": "Ratio failure",
    "issue.PATH_QUALITY_COVERAGE_INCOMPLETE": (
        "Path Quality coverage incomplete — WARN reflects missing evaluable path evidence "
        "on some Trials, not a detected path failure"
    ),
    "issue.PATH_REVERSAL_OR_JITTER_FAIL": "Path reversal or jitter failure",
    "issue.NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR": "No path evidence above noise floor",
    "obs.dpi_control_identification": "DPI control identification",
    "obs.dpi_stage_count": "DPI stage count",
    "obs.dpi_step_up_cycle": "DPI step / cycle behavior",
    "obs.dpi_reset_check": "Unexpected DPI reset check",
    "obs.dpi_indicator_check": "DPI indicator check",
}

_ZH_TW = {
    **_EN,
    "app.title": "滑鼠 DPI 工具",
    "nav.setup": "設定",
    "nav.capture": "擷取",
    "nav.results": "結果",
    "nav.settings": "偏好",
    "setup.title": "工作階段設定",
    "setup.subtitle": "本工作階段的受測裝置與量測設定。",
    "setup.vendor": "廠商",
    "setup.model": "型號",
    "setup.notes": "備註",
    "setup.notes_deviations": "備註／偏差",
    "setup.revert": "還原變更",
    "setup.apply_failed": "無法套用設定變更。",
    "setup.surface": "追蹤表面",
    "setup.surface_hint": "滑鼠光學 Sensor 直接觀察的表面（不是治具載台材質）。",
    "setup.fixture_type": "治具／接觸條件備註",
    "setup.method": "治具／測試方法",
    "setup.method_recovered": (
        "已儲存的測試方法不是支援的值。請從清單選擇方法後再按「套用」。"
    ),
    "setup.ctx_notes": "工程備註",
    "setup.dpi_configuration_source": "DPI 設定來源",
    "setup.dpi_source.hardware_control": "硬體控制",
    "setup.dpi_source.onboard_profile": "板載設定檔",
    "setup.dpi_source.vendor_software": "廠商軟體",
    "setup.dpi_source.other": "其他",
    "setup.dpi_source.unknown": "未知",
    "setup.control_software_state": "控制軟體狀態",
    "setup.control_state.not_running": "未執行",
    "setup.control_state.ui_open": "介面開啟",
    "setup.control_state.background_service_present": "背景服務存在",
    "setup.control_state.unknown": "未知",
    "setup.control_software_name": "控制軟體名稱",
    "setup.control_software_version": "控制軟體版本",
    "setup.profile_note": "設定檔備註",
    "setup.measurement_system_uncertainty_note": "量測系統不確定度備註",
    "setup.reference_uncertainty_pct": "參考不確定度（%）",
    "setup.reference_uncertainty_unset": "—",
    "setup.distance": "物理距離",
    "setup.unit": "單位",
    "setup.apply": "套用",
    "setup.applied": "已套用。本次測試將使用 {distance} {unit}。",
    "setup.applied_with_mm": "已套用。本次測試將使用 {distance} {unit}（物理距離 {mm} mm）。",
    "setup.physical_mm_preview": "= {mm} mm（CPI 使用）",
    "setup.unit_keep_number_help": (
        "切換單位會保留你輸入的數字並重新解讀。"
        "例如先輸入 2，再選英吋 → 2 in（= 50.8 mm）。"
        "不會把舊單位的長度自動換算成新數字。"
    ),
    "setup.unit_keep_number_hint": (
        "單位已設為 {unit}，數字保留為 {value}。"
        "請確認上方物理 mm，再按套用。"
    ),
    "setup.optional_meta": "選填備註（量測非必要）",
    "setup.group.dut": "受測裝置",
    "setup.group.measurement": "量測設定",
    "setup.group.notes": "選填備註",
    "setup.meta.fixture_env": "治具／環境",
    "setup.meta.dpi_config": "DPI 設定",
    "setup.meta.uncertainty": "量測不確定度",
    "setup.geometry": "量測幾何",
    "setup.accuracy": "DPI 誤差判定",
    "setup.accuracy.strict": "嚴格（3%）",
    "setup.accuracy.medium": "中等（6%）",
    "setup.accuracy.lenient": "寬鬆（9%）",
    "setup.accuracy.help.FIELD_STRICT": "PASS ≤ 3% · WARN 3–5% · FAIL > 5%",
    "setup.accuracy.help.FIELD_MEDIUM": "PASS ≤ 6% · WARN 6–8% · FAIL > 8%",
    "setup.accuracy.help.FIELD_LENIENT": "PASS ≤ 9% · WARN 9–11% · FAIL > 11%",
    "setup.accuracy_locked": "建立量測證據後，本 Session 的判定標準即鎖定。",
    "trials.tab.active": "有效",
    "trials.tab.rejected": "已拒絕",
    "trials.tab.deleted": "歷史",
    "trials.reject": "拒絕",
    "trials.restore": "還原",
    "trials.delete": "移至歷史",
    "trials.new_session": "新測試 Session",
    "trials.new_session_confirm": (
        "開始新的測試 Session？目前試次證據不會帶入新 Session（匯出前僅存在於記憶體）。"
    ),
    "trials.new_session_done": "已建立新測試 Session，判定標準可再次編輯。",
    "trials.select_one": "請先選擇一筆試次。",
    "trials.summary": (
        "有效 {active} · 已拒絕 {rejected} · 歷史 {deleted} · DPI 組：{groups} · "
        "判定：{criterion}（{bands}）"
    ),
    "trials.filter.all_dpi": "全部 DPI",
    "trials.filter.dpi": "DPI：",
    "trials.sort.label": "排序：",
    "trials.sort.newest": "最新試次",
    "trials.sort.oldest": "最舊試次",
    "trials.sort.dpi_asc": "DPI 低 → 高",
    "trials.sort.dpi_desc": "DPI 高 → 低",
    "trials.sort.abs_error": "絕對誤差最大",
    "trials.sort.status": "狀態嚴重度",
    "trials.col.id": "試次 #",
    "trials.col.id_desc": "試次 # ↓",
    "trials.col.id_asc": "試次 # ↑",
    "trials.col.dpi": "設定 DPI",
    "trials.col.geometry": "幾何",
    "trials.col.distance": "距離",
    "trials.col.cpi": "實測 CPI",
    "trials.col.error": "誤差 %",
    "trials.col.status": "狀態",
    "trials.col.path_quality": "路徑品質",
    "trials.col.direction": "方向",
    "geometry.fixture_vector": "治具向量（任意角度直線）",
    "geometry.directional_axis": "方向軸（X+/X-/Y+/Y−）",
    "geometry.tile.fixture_sub": "任意角度直線移動 · 向量幅度",
    "geometry.tile.axis_sub": "軸向約束移動 · 在擷取頁選擇方向",
    "setup.measurement_locked": (
        "擷取進行中或待納入時，量測距離已鎖定。請先納入、取消或捨棄該次擷取後再修改距離。"
    ),
    "capture.title": "擷取",
    "capture.subtitle": "Raw Input 擷取控制。工程證據留在 domain 層。",
    "capture.start": "開始",
    "capture.admit_and_start": "納入並開始下一筆",
    "capture.stop": "停止",
    "capture.cancel": "取消",
    "capture.admit": "納入試次",
    "capture.discard": "捨棄此次量測",
    "capture.discarded": "已捨棄失敗／待處理擷取。量測設定已解除鎖定。",
    "capture.discarded_for_dpi": "已捨棄待納入量測，以便變更 DPI。",
    "capture.configured_dpi": "設定 DPI",
    "capture.configured_dpi_hint": "由操作者輸入的 DUT 設定（非從滑鼠自動讀取）。",
    "capture.dpi_confirmation_recommended": "建議確認 DUT DPI",
    "capture.ready_move_now": "就緒 — 現在移動",
    "capture.ready_move_hint": (
        "請等到就緒後再移動。徑向量表回中心僅為畫面呈現，不是 Capture 就緒訊號。"
    ),
    "capture.geometry": "幾何",
    "capture.geometry_readonly_hint": "已於設定頁套用 — 請在設定變更幾何後再按套用。",
    "capture.action.starting": "啟動中…",
    "capture.action.processing": "處理中…",
    "capture.help.idle": "設定 Configured DPI、確認上方幾何，然後開始（F5）。",
    "capture.help.arming": "正在武裝擷取 — 請等到 Ready 再移動。",
    "capture.help.running": "依規劃路徑移動滑鼠，然後停止（F5）或取消（Esc）。",
    "capture.help.stopping": "正在結束擷取 — 請稍候。",
    "capture.help.review": "檢視結果後，承認並開始下一筆（F5）或捨棄。",
    "capture.help.discard_only": "此擷取無法承認 — 請捨棄後重試。",
    "capture.direction": "方向",
    "capture.physical_distance": "物理距離",
    "capture.path_trace": "路徑追蹤（工程檢視）",
    "capture.instruction": (
        "請將滑鼠移動完整段預先標記的物理距離。"
        "畫面上的導引僅表示方向，請勿試圖對齊螢幕上的目標記號。"
    ),
    "capture.instruction_fixture": (
        "開始前先將載台貼靠固定基準邊並置於實體起點；開始後勿再進行貼邊／歸位動作。"
        "沿治具行進至實體終點。以徑向目標規的目標半徑為準；路徑追蹤僅供工程檢視。"
        "實體標記距離才是地面真相。"
    ),
    "capture.procedure_hint": (
        "開始前先將載台貼靠固定基準邊並置於實體起點；開始後勿再進行貼邊／歸位動作。"
    ),
    "capture.lane.start": "起點",
    "capture.lane.target": "終點",
    "capture.focus_lost": "因應用程式失去焦點，擷取已取消。請重新量測。",
    "capture.runtime_diag": "執行診斷",
    "capture.admitted": "已納入試次 {trial_id}。",
    "capture.admitted_next": "已納入試次 {trial_id}。正在開始下一筆…",
    "capture.ready_to_admit": (
        "有效量測已完成，但尚未寫入下方試次表。"
        "F5／開始 = 納入並下一筆；「納入試次」= 只納入。"
        "若要改 DPI，直接改設定即可（會自動捨棄本次待納入）。"
    ),
    "direction.X+": "X+ · 左 → 右",
    "direction.X-": "X- · 右 → 左",
    "direction.Y+": "Y+ · 下 → 上",
    "direction.Y-": "Y- · 上 → 下",
    "capture.poster.empty_title": "最新試次",
    "capture.poster.empty_body": "尚無擷取試次",
    "capture.poster.pending": "待納入 — 尚未寫入表格（F5 = 納入並下一筆；改 DPI = 捨棄）",
    "capture.poster.admitted": "已納入試次 {trial_id}",
    "capture.poster.last_admitted": "上次納入：試次 {trial_id}",
    "capture.poster.error": "誤差 {error}%",
    "capture.integrity_pending": "待定（停止後定案）",
    "capture.integrity_na": "不適用",
    "capture.live_provisional": "即時／暫定",
    "capture.tech_details": "技術細節",
    "capture.nav_locked": "量測進行中，請留在擷取頁。",
    "capture.poster.meta": (
        "設定 {configured} DPI · 誤差 {error}% · dx={dx} dy={dy} · "
        "primary={primary} · {mode} · {direction}"
    ),
    "capture.poster.vector_ref": (
        "向量長度參考（斜線治具）: {vector_cpi} CPI — "
        "請改選「治具向量」幾何，官方 CPI 才會用 √(dx²+dy²)。"
    ),
    "capture.poster.fixture_hint": (
        "治具向量：官方 CPI = √(dx²+dy²) / 英吋，對應已知物理距離。"
    ),
    "results.title": "結果",
    "results.subtitle": "來自有效定量證據的 Findings 總覽。",
    "results.summary": "有效試次: {trials} · 組數: {groups} · 相對 DPI 縮放對數: {ratios}",
    "results.empty_title": "尚無量測結果。",
    "results.empty_body": "完成至少一筆量測試次後，將開始建立工程 evidence。",
    "results.empty_go_capture": "前往擷取",
    "results.empty_open_guide": "開啟使用指南",
    "results.research": "研究／未評估",
    "results.groups_title": "DPI 組摘要",
    "results.ratios_title": "相對 DPI 縮放",
    "results.ratios_hint": "比較實測 CPI 階比與設定比例——相對縮放，非絕對 CPI 接近程度。",
    "results.scale_pattern_title": "跨 DPI 尺度模式",
    "results.findings_title": "量測 Findings",
    "results.evidence_title": "DPI Evidence 摘要",
    "results.eng_diag_title": "進階／工程診斷",
    "results.eng_diag_collapsed_hint": (
        "試次序列、CPI 分布、估計速度關聯、READY 至首次移動等診斷。"
    ),
    "results.eng_diag_hint": (
        "依 Session 證據建立的描述性診斷檢視——非 Findings。"
        "估計移動速度並非真實物理速度。"
    ),
    "results.dpi_filter": "DPI 篩選",
    "results.dpi_filter_all": "全部 DPI",
    "results.trial_sequence_title": "試次序列 CPI 誤差",
    "results.trial_dist_title": "各 DPI 的 CPI 誤差分布",
    "results.speed_error_title": "CPI 誤差 vs 估計移動速度",
    "results.speed_unavailable": "本 Session 無移動時序證據。",
    "results.speed_corr_wording": (
        "部分 DPI 組內可見估計移動速度與 CPI 誤差的關聯；方向與強度並非各組一致。"
        "非因果 Finding。event_count 不是速度。"
    ),
    "results.latency_error_title": "CPI 誤差 vs READY 至首次移動延遲",
    "results.latency_error_hint": (
        "僅描述性——較早開始移動的試次是否與較長停留不同。"
        "無 PASS/WARN/FAIL；不虛構最低安全延遲。"
    ),
    "results.trends_title": "DPI 行為趨勢",
    "results.trends_hint": "圖表僅描述既有組摘要，不構成 Finding，亦非高 DPI 插值判定。",
    "results.group.dpi": "設定 DPI",
    "results.group.trials": "試次數",
    "results.group.avg_cpi": "平均實測 CPI",
    "results.group.max_error": "最大 |誤差| %",
    "results.group.cv": "CPI CV %",
    "results.group.status": "狀態",
    "results.ratio.from": "從 DPI",
    "results.ratio.to": "到 DPI",
    "results.ratio.expected": "設定比例",
    "results.ratio.measured": "實測比例",
    "results.ratio.error": "比例誤差 %",
    "results.ratio.status": "狀態",
    "results.report.generate": "產生報告…",
    "results.report.choose_folder": "選擇報告輸出資料夾",
    "results.report.busy": "正在產生報告…",
    "results.report.done": "報告已寫入 {folder}：\n{html}\n{json}",
    "results.report.failed": "報告失敗：{error}",
    "results.report.method_invalid": (
        "方法中繼資料無效。請先選擇支援的測試方法再匯出。"
    ),
    "charts.measured_cpi.title": "實測 CPI 對設定 DPI",
    "charts.measured_cpi.caption": (
        "比較各 DPI 群組的平均實測 CPI 與理想 1:1 目標；實測線越接近理想線，代表 Effective CPI 越接近設定值。"
    ),
    "charts.max_error.title": "各 DPI 最大 CPI 誤差",
    "charts.max_error.caption": (
        "顯示每個 DPI 群組中最大的絕對 CPI 誤差，並與本 Session 的 Accuracy 判定門檻比較。"
    ),
    "charts.repeatability.title": "重複性（CPI CV）",
    "charts.repeatability.caption": (
        "CPI CV 表示同一 DPI 多次量測的離散程度；數值越低代表重複性越高。"
    ),
    "charts.obs.cpi.all_below_ideal": (
        "所有群組平均實測 CPI 皆低於理想 1:1 參考線；最大群組誤差為 {max_abs_error_pct}%。"
    ),
    "charts.obs.cpi.all_above_ideal": (
        "所有群組平均實測 CPI 皆高於理想 1:1 參考線；最大群組誤差為 {max_abs_error_pct}%。"
    ),
    "charts.obs.cpi.mixed_vs_ideal": (
        "群組平均實測 CPI 同時出現高於與低於理想 1:1 參考線；最大群組誤差為 {max_abs_error_pct}%。"
    ),
    "charts.obs.cpi.no_data": "本 Session 尚無 DPI 群組平均值。",
    "charts.obs.error.band_counts": (
        "依最大絕對 CPI 誤差對照 Accuracy 門檻：PASS {pass} · WARN {warn} · FAIL {fail}"
        "（PASS ≤ {pass_pct:g}% · WARN > {pass_pct:g}%–{fail_pct:g}% · FAIL > {fail_pct:g}%）。"
    ),
    "charts.obs.error.no_data": "本 Session 尚無 DPI 群組誤差值。",
    "charts.obs.cv.highest": "本 Session 中 {dpi} DPI 的 CPI CV 最高（{cv}%）。",
    "charts.obs.cv.no_data": "本 Session 尚無 DPI 群組 CPI CV。",
    "results.summary": "有效試次: {trials} · 組數: {groups} · 相對 DPI 縮放對數: {ratios}",

    "capture.start_f5": "開始  F5",
    "capture.stop_f5": "停止  F5",
    "capture.cancel_esc": "取消  Esc",
    "capture.admit_and_start_f5": "納入並開始下一筆  F5",
    "capture.shortcut_hint": "快捷鍵：F5 開始／停止 · Esc 取消",
    "capture.how_to_measure": "？如何量測",
    "capture.how_to_measure_body": (
        "<ol>"
        "<li>選擇配置 DPI。</li>"
        "<li>將載台置於標記的實體起點。</li>"
        "<li><b>在</b> F5／開始之前：將載台貼靠選定的機械基準邊並維持預壓；全程保持接觸。</li>"
        "<li>按 F5／開始。</li>"
        "<li>僅沿治具行進至實體終點（開始後勿再貼邊／歸位）。</li>"
        "<li>停在標記終點；按 F5／停止。</li>"
        "<li>檢視 Integrity／Path Quality／CPI，再納入（Admit）。</li>"
        "</ol>"
        "<p>實體標記行進距離為地面真相。徑向規＝視覺化／導引；路徑追蹤＝工程視覺化。"
        "即使 Accuracy 或 Path Quality 為 PASS，非直線路徑追蹤仍可能代表操作／治具運動變異。"
        "Accuracy PASS 不證明路徑機械上理想；Path Quality PASS 不證明治具幾何完全筆直。"
        "F5／Esc 為快捷鍵，非必用。</p>"
    ),
    "capture.dpi_presets": "預設值",
    "capture.dpi_spin_tip": "配置 DPI（唯一真相來源）",
    "capture.dpi_preset_tip": "跳至常用配置 DPI 預設值",
    "setup.accuracy_locked_short": "已鎖定",
    "help.guide.title": "使用指南",
    "help.guide.open": "？使用指南",
    "help.section.quick_start": "A. 快速開始",
    "help.body.quick_start": (
        "設定 DPI 與距離 → 擷取 → <b>開始前</b>將載台貼靠基準邊並置於實體起點 → "
        "僅沿治具行進 → F5 停止 → 檢視 → 納入。開始後勿再貼邊／歸位。"
        "實體距離才是地面真相。更正操作程序後請開啟<b>新</b>測試 Session，勿與舊程序試次混算。"
    ),
    "help.section.shortcuts": "B. 鍵盤快捷鍵",
    "help.body.shortcuts": "F5 開始／停止 · Esc 取消。擷取頁按鈕旁也有提示。",
    "help.section.methods": "C. 量測方法",
    "help.body.methods": (
        "<b>Fixture Vector</b>：任意角度直線；CPI 使用向量長度。<br/>"
        "<b>Directional Axis</b>：X+/X-/Y+/Y−；CPI 使用軸向投影。"
    ),
    "help.section.findings": "D. 解讀 Findings",
    "help.body.findings": (
        "Accuracy：Effective CPI 與配置 DPI 的接近程度（絕對）。<br/>"
        "Repeatability：同一 DPI 群組內的一致性（CV 越低越好）。<br/>"
        "相對 DPI 縮放：比較不同 DPI 檔位的實測 CPI 比例與設定比例，用於觀察相對縮放一致性；"
        "不代表已證明 Sensor 線性或原生能力。<br/>"
        "Path Quality：PASS 表示未偵測到目前 V1 規則所定義的明顯反向／抖動路徑異常；"
        "不代表 Tracking／Sensor／Native capability，也不代表治具幾何完全筆直。"
        "覆蓋不完整的 WARN 表示部分 Trial 缺少可評估路徑證據（不一定是路徑失敗）。"
    ),
    "help.section.trends": "E. 解讀 DPI 行為趨勢圖",
    "help.body.trends": (
        "圖 1：越接近 1:1 理想線越好。<br/>"
        "圖 2：誤差越低越好；PASS／WARN／FAIL 依本 Session 門檻。<br/>"
        "圖 3：CPI CV 越低代表重複性越好。"
    ),
    "help.section.criterion": "F. 判定標準",
    "help.body.criterion": (
        "Strict／Medium／Lenient 設定 PASS 與 FAIL 的 CPI 誤差上限（WARN 為中間帶）。"
        "建立量測證據後即鎖定。"
    ),
    "help.section.limits": "G. 方法限制",
    "help.body.limits": (
        "本工具以已知實體距離與 Windows Raw Input 驗證 Effective CPI。"
        "V1 不證明原生感測器解析度，也不對韌體插值／縮放下結論。"
        "設定的實體距離必須對應實際 Sensor 在選定起點與終點之間的位移——"
        "若治具外寬、開口尺寸或載台外殼邊緣與 Sensor 行程不一致，請勿僅量測那些尺寸。"
        "建議以獨立實體量具確認起點到終點位移後，再對 Sensor 下結論。"
    ),
    "finding.metric.max_individual_error": "個別 Trial 最大 CPI 誤差",
    "finding.metric.groups_dist": "群組數",
    "finding.metric.active_trials": "有效 Trials",
    "finding.metric.max_cpi_cv": "最大 CPI CV",
    "finding.metric.min_trials": "每組最少 Trials",
    "finding.metric.max_ratio_error": "最大｜比值誤差｜",
    "finding.metric.pairs_dist": "配對數",
    "finding.metric.pq_pass": "Path Quality PASS",
    "finding.metric.pq_warn": "WARN",
    "finding.metric.pq_fail": "FAIL",
    "finding.metric.pq_trials": "含 PQ 的 Trials",
    "finding.help.accuracy": "量測 Effective CPI 與配置 DPI 的接近程度。",
    "finding.help.repeatability": "同一 DPI 群組內重複量測的一致性。",
    "finding.help.ratio": (
        "比較不同 DPI 檔位的實測 CPI 比例與設定比例，用於觀察相對縮放一致性；"
        "不代表已證明 Sensor 線性或原生能力。"
    ),
    "finding.help.path_quality": (
        "PASS 表示未偵測到目前 V1 規則所定義的明顯反向／抖動路徑異常；"
        "不代表治具幾何完全筆直或完全沒有側向移動。"
        "覆蓋不完整的 WARN 表示部分 Trial 缺少可評估路徑證據（例如 NOT_EVALUATED）——"
        "不是已偵測到路徑失敗。非 Tracking／Sensor／Native capability。"
    ),
    "finding.help.research": "保留供未來特性分析；V1 不會僅依 Raw Input 推斷這些屬性。",
    "charts.how_to_read": "如何解讀此圖",
    "charts.measured_cpi.legend": "平均量測 · 理想 1:1",
    "charts.max_error.legend": "最大個別｜誤差｜% · PASS／WARN／FAIL 門檻",
    "charts.repeatability.legend": "CPI CV % · 重複性 PASS／WARN／FAIL 門檻",
    "charts.measured_cpi.cue": "越接近灰色 1:1 理想線，代表 Effective CPI 越接近設定值。",
    "charts.max_error.cue": "越低越好；PASS／WARN／FAIL 區間依本 Session 的判定門檻。",
    "charts.repeatability.cue": "越低代表同一 DPI 的多次量測越一致。",
    "charts.measured_cpi.x": "配置 DPI",
    "charts.measured_cpi.y": "平均量測 CPI",
    "charts.max_error.x": "配置 DPI",
    "charts.max_error.y": "最大絕對 CPI 誤差（%）",
    "charts.repeatability.x": "配置 DPI",
    "charts.repeatability.y": "CPI CV（%）",
    "charts.measured_cpi.metric_note": (
        "圖表摘要使用「群組平均 CPI 與設定值的偏差」。"
        "Accuracy Finding 使用「個別 Trial 最大｜誤差｜」——兩者不同。"
    ),
    "charts.max_error.metric_note": "使用各群組個別 Trial 的最大絕對 CPI 誤差（與 Accuracy 同源）。",
    "charts.obs.cpi.all_below_ideal": (
        "所有群組平均量測值皆低於 1:1 理想線；"
        "群組平均 CPI 與設定值的最大偏差為 {max_mean_deviation_pct}%。"
    ),
    "charts.obs.cpi.all_above_ideal": (
        "所有群組平均量測值皆高於 1:1 理想線；"
        "群組平均 CPI 與設定值的最大偏差為 {max_mean_deviation_pct}%。"
    ),
    "charts.obs.cpi.mixed_vs_ideal": (
        "群組平均量測值同時分布於 1:1 理想線上下；"
        "群組平均 CPI 與設定值的最大偏差為 {max_mean_deviation_pct}%。"
    ),
    "report.interpretation.title": "如何解讀本報告",
    "report.interpretation.body": (
        "Accuracy：Effective CPI 相對配置 DPI 的絕對接近程度（個別 Trial 最大誤差）。<br/>"
        "相對 DPI 縮放：實測 CPI 階比相對設定階比（相對縮放——非絕對 CPI 接近程度）。<br/>"
        "絕對 CPI 可能共享共同偏差，而相對 DPI 階比仍可保持一致；兩者描述不同性質。<br/>"
        "Repeatability：同一 DPI 群組一致性（CPI CV 越低越好）。<br/>"
        "Path Quality：PASS 表示未偵測到 V1 反向／抖動規則異常；覆蓋不完整 WARN 表示部分 "
        "Trial 缺少可評估路徑證據——不一定是路徑失敗。<br/>"
        "跨 DPI 尺度模式：描述性群組平均尺度——非 Finding，亦不推定根因。<br/>"
        "量測 CPI 圖：越接近 1:1 越好（群組平均偏差 ≠ Accuracy 最大誤差）。<br/>"
        "誤差圖：越低越好；PASS／WARN／FAIL 依 Session 門檻。<br/>"
        "CV 圖：越低代表重複性越好。"
    ),

    "scale.pattern.title": "跨 DPI 尺度模式",
    "scale.pattern.disclaimer": "僅供描述性診斷——非 Finding；不自動推定根因。",
    "scale.pattern.none": "DPI 群組平均不足，無法形成尺度模式。",
    "scale.pattern.groups": "已評估 DPI 群組：{n}",
    "scale.pattern.scale_range": (
        "正規化尺度（平均 CPI／設定）：{min_s} – {max_s}"
        "（平均 {mean_s}，中位 {med_s}，跨度 {spread}）"
    ),
    "scale.pattern.dev_range": (
        "群組平均相對設定偏差約 {lo:+.2f}% 至 {hi:+.2f}%。"
    ),
    "scale.pattern.common_with_ratio": (
        "本 Session 各 DPI 群組呈現相近的共同偏差，而相鄰 DPI 的實測比例仍接近設定比例"
        "（最大｜比值誤差｜ {err}%）；建議進一步確認量測系統與產品 CPI 校正——"
        "非自動治具或 Sensor 判定。"
    ),
    "scale.pattern.common": (
        "本 Session 各 DPI 群組呈現相近的共同偏差；建議進一步確認量測系統與產品 CPI 校正——"
        "非自動治具或 Sensor 判定。"
    ),
    "scale.pattern.mixed": (
        "各 DPI 群組尺度差異明顯（或正負混雜），不描述為共同尺度偏差模式。"
    ),
    "scale.pattern.no_root_cause": (
        "可能原因包含行程距離定義、治具幾何／預壓、起終點基準、產品整體 CPI 偏差或其他共同效應。"
        "本工具不會自動擇一。"
    ),

    "fixture.diag.title": "治具／移動診斷",
    "fixture.diag.disclaimer": "僅供描述性診斷，不代表治具或 Sensor 的 PASS/FAIL 判定。",
    "fixture.diag.none": "治具／移動診斷：尚無 Fixture Vector 試次。",
    "fixture.diag.avg_straightness": "平均直線度：{value}%",
    "fixture.diag.min_straightness": "最低直線度：{value}%",
    "fixture.diag.max_path_excess": "最大路徑過量：{value}%",
    "fixture.diag.mean_heading": "治具軸向方位：{value}°",
    "fixture.diag.heading_spread": "軸向方位離散：{value}°",
    "fixture.diag.axis_orientation": "治具軸向方位：{value}°",
    "fixture.diag.axis_spread": "軸向方位離散：{value}°",
    "fixture.diag.axis_note": (
        "軸向方位採軸向（模 180°）統計。絕對角度不是品質分數；"
        "反向行進不會膨脹離散。"
    ),
    "fixture.diag.polarity": (
        "行進極性——正向：{forward} · 反向：{reverse}（僅描述）。"
    ),
    "fixture.diag.avg_straightness_ceiling": "平均直線度：{value}%（指標上限）",
    "fixture.diag.min_straightness_ceiling": "最低直線度：{value}%（指標上限）",
    "fixture.diag.path_excess_ne": "路徑過量：NOT_EVALUATED（path_total < vector，噪音門檻語意）",
    "fixture.diag.heading_note": (
        "軸向方位離散反映治具軸一致性（模 180°），不是治具直線度分數。"
    ),
    "fixture.diag.per_dpi_title": "各 DPI 移動一致性（描述性）：",
    "fixture.diag.per_dpi_header": (
        "DPI｜試次｜軸向方位｜軸向離散｜正／反｜平均直線度｜路徑過量"
    ),
    "fixture.diag.ceiling_footnote": "* 直線度達 Path Quality 指標上限（≤100%）",
    "fixture.diag.missing": "規範證據不足：{fields}",
    "help.section.fixture_motion": "H. 治具／移動診斷",
    "help.body.fixture_motion": (
        "斜向但筆直的治具是合法的。Fixture Vector 使用軸向（模 180°）方位——"
        "θ 與 θ+180° 為同一軸。請看直線度、路徑過量與軸向方位離散——"
        "不可僅依 CPI 誤差歸因。僅供描述，非治具或 Sensor 的 PASS/FAIL。"
        "Path Quality PASS 表示未觸發 V1 反向／抖動規則——不代表實體治具完全筆直。"
    ),
    "settings.title": "偏好設定",
    "settings.subtitle": "主題與語言僅影響介面，不會寫入 Session 工程證據。",
    "settings.theme": "主題",
    "settings.locale": "語言",
    "theme.light": "淺色",
    "theme.dark": "深色",
    "theme.system": "跟隨系統",
    "unit.mm": "毫米 (mm)",
    "unit.cm": "公分 (cm)",
    "unit.inch": "英吋 (inch)",
    "method.hand_drag": "手動拖曳",
    "method.click_click": "點擊—點擊",
    "method.fixture": "治具",
    "method.synthetic": "合成",
    "method.unknown": "未知",
    "finding.accuracy": "準確度",
    "finding.repeatability": "重複性",
    "finding.ratio": "相對 DPI 縮放",
    "finding.path_quality": "路徑品質",
    "issue.PATH_QUALITY_COVERAGE_INCOMPLETE": (
        "Path Quality 覆蓋不完整——WARN 反映部分 Trial 缺少可評估路徑證據，"
        "不是已偵測到路徑失敗"
    ),
    "finding.metric.pq_not_evaluated": "NOT_EVALUATED",
    "finding.metric.pq_coverage_note": "覆蓋說明",
    "finding.metric.pq_coverage_value": (
        "WARN 反映路徑證據覆蓋不完整（{n} 筆 NOT_EVALUATED）；未偵測到 PQ FAIL。"
    ),
    "status.PASS": "通過",
    "status.WARN": "警告",
    "status.FAIL": "失敗",
    "status.NOT_TESTED": "未測試",
    "status.NOT_EVALUATED": "未評估",

    # UI-3A remaining primary-surface zh-TW overrides
    "setup.dut": "DUT",
    "setup.movement_mode": "移動模式",
    "setup.accuracy_locked": "建立量測證據後，本 Session 的判定標準即鎖定。",
    "capture.state": "狀態",
    "capture.status": "狀態",
    "capture.nets": "Nets",
    "capture.events": "事件",
    "capture.devices": "裝置",
    "capture.mismatch": "已選：{selected} · 觀測移動：{observed}",
    "capture.zero_primary": "所選方向沒有主軸移動。",
    "capture.display.idle": "待命",
    "capture.display.starting": "正在開始…",
    "capture.display.capturing": "擷取中",
    "capture.display.stopping": "正在停止…",
    "capture.display.cancelling": "正在取消…",
    "capture.display.discarding": "正在捨棄…",
    "capture.display.valid_stopped": "已停止 — 可納入",
    "capture.display.direction_mismatch": "方向不符",
    "capture.display.zero_primary": "主軸計數為 0",
    "capture.display.cancelled": "已取消",
    "capture.display.error": "錯誤",
    "capture.display.stopped": "已停止",
    "capture.path_quality": "路徑品質",
    "capture.primary_counts": "主軸計數",
    "capture.integrity": "完整性",
    "results.trials": "有效試次",
    "results.groups": "群組",
    "results.ratios": "相對 DPI 縮放",
    "results.group.cv": "CPI CV %",
    "results.group.max_error": "最大個別｜誤差｜%",
    "finding.metric.pq_pass": "路徑品質 PASS",
    "finding.metric.pq_warn": "WARN",
    "finding.metric.pq_fail": "FAIL",
    "finding.manual_observations": "手動觀察",
    "finding.linearity": "線性度",
    "finding.scaling_evidence": "縮放證據",
    "finding.native_capability": "原生能力",
    "status.SKIP": "略過",

}

_ZH_CN = {
    **_EN,
    "app.title": "鼠标 DPI 工具",
    "nav.setup": "设置",
    "nav.capture": "采集",
    "nav.results": "结果",
    "nav.settings": "偏好",
    "setup.title": "会话设置",
    "setup.subtitle": "本会话的 DUT 元数据与测量情境。",
    "setup.vendor": "厂商",
    "setup.model": "型号",
    "setup.notes": "备注",
    "setup.distance": "距离",
    "setup.unit": "单位",
    "setup.apply": "应用",
    "capture.title": "采集",
    "capture.subtitle": "Raw Input 采集控制。工程证据保留在 domain 层。",
    "capture.start": "开始",
    "capture.stop": "停止",
    "capture.cancel": "取消",
    "capture.admit": "纳入试次",
    "capture.configured_dpi": "设定 DPI",
    "capture.direction": "方向",
    "capture.physical_distance": "物理距离",
    "capture.instruction": (
        "请将鼠标移动完整段预先标记的物理距离。"
        "屏幕上的引导仅表示方向，请勿试图对齐屏幕上的目标标记。"
    ),
    "capture.lane.start": "起点",
    "capture.lane.target": "终点",
    "direction.X+": "X+ · 左 → 右",
    "direction.X-": "X- · 右 → 左",
    "direction.Y+": "Y+ · 下 → 上",
    "direction.Y-": "Y- · 上 → 下",
    "results.title": "结果",
    "results.subtitle": "来自有效定量证据的独立 Findings 维度。",
    "settings.title": "偏好设置",
    "settings.subtitle": "主题与语言只影响界面，不会写入 Session 工程证据。",
    "settings.theme": "主题",
    "settings.locale": "语言",
    "theme.light": "浅色",
    "theme.dark": "深色",
    "theme.system": "跟随系统",
    "unit.mm": "毫米 (mm)",
    "unit.cm": "厘米 (cm)",
    "unit.inch": "英寸 (inch)",
    "finding.accuracy": "准确度",
    "finding.repeatability": "重复性",
    "finding.ratio": "比例",
    "finding.path_quality": "路径质量",
    "status.PASS": "通过",
    "status.WARN": "警告",
    "status.FAIL": "失败",
    "status.NOT_TESTED": "未测试",
    "status.NOT_EVALUATED": "未评估",
}

_JA = {
    **_EN,
    "app.title": "マウス DPI ツール",
    "nav.setup": "セットアップ",
    "nav.capture": "キャプチャ",
    "nav.results": "結果",
    "nav.settings": "設定",
    "setup.title": "セッション設定",
    "setup.subtitle": "このセッションの DUT メタデータと測定コンテキスト。",
    "setup.vendor": "ベンダー",
    "setup.model": "モデル",
    "setup.notes": "メモ",
    "setup.distance": "距離",
    "setup.unit": "単位",
    "setup.apply": "適用",
    "capture.title": "キャプチャ",
    "capture.subtitle": "Raw Input キャプチャ操作。工学エビデンスはドメイン層に残します。",
    "capture.start": "開始",
    "capture.stop": "停止",
    "capture.cancel": "キャンセル",
    "capture.admit": "試行を採用",
    "capture.configured_dpi": "設定 DPI",
    "capture.direction": "方向",
    "capture.physical_distance": "物理距離",
    "capture.instruction": (
        "マウスをあらかじめ印した物理距離いっぱいまで動かしてください。"
        "画面のガイドは方向の目安です。画面上の目標マーカーに合わせないでください。"
    ),
    "capture.lane.start": "開始",
    "capture.lane.target": "目標",
    "direction.X+": "X+ · 左 → 右",
    "direction.X-": "X- · 右 → 左",
    "direction.Y+": "Y+ · 下 → 上",
    "direction.Y-": "Y- · 上 → 下",
    "results.title": "結果",
    "results.subtitle": "有効な定量エビデンスから得た独立 Findings。",
    "settings.title": "環境設定",
    "settings.subtitle": "テーマと言語は UI 設定であり、Session 証拠ではありません。",
    "settings.theme": "テーマ",
    "settings.locale": "言語",
    "theme.light": "ライト",
    "theme.dark": "ダーク",
    "theme.system": "システムに従う",
    "unit.mm": "ミリメートル (mm)",
    "unit.cm": "センチメートル (cm)",
    "unit.inch": "インチ (inch)",
    "finding.accuracy": "精度",
    "finding.repeatability": "再現性",
    "finding.ratio": "比率",
    "finding.path_quality": "パス品質",
    "status.PASS": "合格",
    "status.WARN": "警告",
    "status.FAIL": "不合格",
    "status.NOT_TESTED": "未実施",
    "status.NOT_EVALUATED": "未評価",
}

_KO = {
    **_EN,
    "app.title": "마우스 DPI 도구",
    "nav.setup": "설정",
    "nav.capture": "캡처",
    "nav.results": "결과",
    "nav.settings": "환경설정",
    "setup.title": "세션 설정",
    "setup.subtitle": "이 세션의 DUT 메타데이터와 측정 컨텍스트.",
    "setup.vendor": "제조사",
    "setup.model": "모델",
    "setup.notes": "메모",
    "setup.distance": "거리",
    "setup.unit": "단위",
    "setup.apply": "적용",
    "capture.title": "캡처",
    "capture.subtitle": "Raw Input 캡처 제어. 엔지니어링 증거는 도메인 계층에 유지됩니다.",
    "capture.start": "시작",
    "capture.stop": "중지",
    "capture.cancel": "취소",
    "capture.admit": "트라이얼 채택",
    "capture.configured_dpi": "설정 DPI",
    "capture.direction": "방향",
    "capture.physical_distance": "물리 거리",
    "capture.instruction": (
        "미리 표시한 물리 거리 전체를 마우스 이동으로 완료하세요."
        "화면 가이드는 방향 안내용이며, 화면 목표 표시에 맞추지 마세요."
    ),
    "capture.lane.start": "시작",
    "capture.lane.target": "목표",
    "direction.X+": "X+ · 왼쪽 → 오른쪽",
    "direction.X-": "X- · 오른쪽 → 왼쪽",
    "direction.Y+": "Y+ · 아래 → 위",
    "direction.Y-": "Y- · 위 → 아래",
    "results.title": "결과",
    "results.subtitle": "유효한 정량 증거에서 도출된 독립 Findings 차원.",
    "settings.title": "환경설정",
    "settings.subtitle": "테마와 언어는 UI 환경설정이며 Session 증거가 아닙니다.",
    "settings.theme": "테마",
    "settings.locale": "언어",
    "theme.light": "라이트",
    "theme.dark": "다크",
    "theme.system": "시스템 따름",
    "unit.mm": "밀리미터 (mm)",
    "unit.cm": "센티미터 (cm)",
    "unit.inch": "인치 (inch)",
    "finding.accuracy": "정확도",
    "finding.repeatability": "반복성",
    "finding.ratio": "비율",
    "finding.path_quality": "경로 품질",
    "status.PASS": "통과",
    "status.WARN": "경고",
    "status.FAIL": "실패",
}

_DE = {
    **_EN,
    "app.title": "Maus-DPI-Werkzeug",
    "nav.setup": "Einrichtung",
    "nav.capture": "Erfassung",
    "nav.results": "Ergebnisse",
    "nav.settings": "Einstellungen",
    "setup.title": "Sitzungseinrichtung",
    "setup.subtitle": "DUT-Metadaten und Messkontext für diese Sitzung.",
    "setup.vendor": "Hersteller",
    "setup.model": "Modell",
    "setup.notes": "Notizen",
    "setup.distance": "Distanz",
    "setup.unit": "Einheit",
    "setup.apply": "Übernehmen",
    "capture.title": "Erfassung",
    "capture.subtitle": "Raw-Input-Steuerung. Engineering-Evidenz bleibt in der Domänenschicht.",
    "capture.start": "Start",
    "capture.stop": "Stopp",
    "capture.cancel": "Abbrechen",
    "capture.admit": "Versuch übernehmen",
    "capture.configured_dpi": "Konfiguriertes DPI",
    "capture.direction": "Richtung",
    "capture.physical_distance": "Physische Distanz",
    "capture.instruction": (
        "Bewegen Sie die Maus über die vollständige vorgemarkte physische Distanz. "
        "Die Bildschirmanzeige dient nur der Richtung; richten Sie den Cursor nicht "
        "am Zielmarker aus."
    ),
    "capture.lane.start": "START",
    "capture.lane.target": "ZIEL",
    "direction.X+": "X+ · Links → Rechts",
    "direction.X-": "X- · Rechts → Links",
    "direction.Y+": "Y+ · Unten → Oben",
    "direction.Y-": "Y- · Oben → Unten",
    "results.title": "Ergebnisse",
    "results.subtitle": "Unabhängige Findings-Dimensionen aus aktiver quantitativer Evidenz.",
    "settings.title": "Einstellungen",
    "settings.subtitle": "Design und Sprache sind Präsentationspräferenzen — keine Session-Evidenz.",
    "settings.theme": "Design",
    "settings.locale": "Sprache",
    "theme.light": "Hell",
    "theme.dark": "Dunkel",
    "theme.system": "System folgen",
    "unit.mm": "Millimeter (mm)",
    "unit.cm": "Zentimeter (cm)",
    "unit.inch": "Zoll (inch)",
    "finding.accuracy": "Genauigkeit",
    "finding.repeatability": "Wiederholbarkeit",
    "finding.ratio": "Verhältnis",
    "finding.path_quality": "Pfadqualität",
    "status.PASS": "Bestanden",
    "status.WARN": "Warnung",
    "status.FAIL": "Fehlgeschlagen",
    "status.NOT_TESTED": "Nicht getestet",
    "status.NOT_EVALUATED": "Nicht bewertet",
}

_FR = {
    **_EN,
    "app.title": "Outil DPI souris",
    "nav.setup": "Configuration",
    "nav.capture": "Capture",
    "nav.results": "Résultats",
    "nav.settings": "Préférences",
    "setup.title": "Configuration de session",
    "setup.subtitle": "Métadonnées DUT et contexte de mesure pour cette session.",
    "setup.vendor": "Fabricant",
    "setup.model": "Modèle",
    "setup.notes": "Notes",
    "setup.distance": "Distance",
    "setup.unit": "Unité",
    "setup.apply": "Appliquer",
    "capture.title": "Capture",
    "capture.subtitle": "Commandes Raw Input. Les preuves restent dans la couche domaine.",
    "capture.start": "Démarrer",
    "capture.stop": "Arrêter",
    "capture.cancel": "Annuler",
    "capture.admit": "Admettre l'essai",
    "capture.configured_dpi": "DPI configuré",
    "capture.direction": "Sens de mesure",
    "capture.physical_distance": "Distance physique",
    "capture.instruction": (
        "Déplacez la souris sur toute la distance physique pré-marquée. "
        "Le guide à l'écran n'indique que la direction ; n'essayez pas d'aligner "
        "le curseur sur le marqueur cible."
    ),
    "capture.lane.start": "DÉBUT",
    "capture.lane.target": "CIBLE",
    "direction.X+": "X+ · Gauche → Droite",
    "direction.X-": "X- · Droite → Gauche",
    "direction.Y+": "Y+ · Bas → Haut",
    "direction.Y-": "Y- · Haut → Bas",
    "results.title": "Résultats",
    "results.subtitle": "Dimensions Findings indépendantes à partir des preuves quantitatives actives.",
    "settings.title": "Préférences",
    "settings.subtitle": "Thème et langue sont des préférences d'interface — pas des preuves Session.",
    "settings.theme": "Thème",
    "settings.locale": "Langue",
    "theme.light": "Clair",
    "theme.dark": "Sombre",
    "theme.system": "Suivre le système",
    "unit.mm": "millimètres (mm)",
    "unit.cm": "centimètres (cm)",
    "unit.inch": "pouces (inch)",
    "finding.accuracy": "Exactitude",
    "finding.repeatability": "Répétabilité",
    "finding.ratio": "Ratio",
    "finding.path_quality": "Qualité de trajectoire",
    "status.PASS": "Réussi",
    "status.WARN": "Avertissement",
    "status.FAIL": "Échec",
}

_ES = {
    **_EN,
    "app.title": "Herramienta DPI de ratón",
    "nav.setup": "Configuración",
    "nav.capture": "Captura",
    "nav.results": "Resultados",
    "nav.settings": "Preferencias",
    "setup.title": "Configuración de sesión",
    "setup.subtitle": "Metadatos DUT y contexto de medición para esta sesión.",
    "setup.vendor": "Fabricante",
    "setup.model": "Modelo",
    "setup.notes": "Notas",
    "setup.distance": "Distancia",
    "setup.unit": "Unidad",
    "setup.apply": "Aplicar",
    "capture.title": "Captura",
    "capture.subtitle": "Controles Raw Input. La evidencia permanece en la capa de dominio.",
    "capture.start": "Iniciar",
    "capture.stop": "Detener",
    "capture.cancel": "Cancelar",
    "capture.admit": "Admitir ensayo",
    "capture.configured_dpi": "DPI configurado",
    "capture.direction": "Dirección",
    "capture.physical_distance": "Distancia física",
    "capture.instruction": (
        "Mueva el ratón a lo largo de toda la distancia física marcada de antemano. "
        "La guía en pantalla solo indica la dirección; no intente alinear el cursor "
        "con el marcador objetivo."
    ),
    "capture.lane.start": "INICIO",
    "capture.lane.target": "OBJETIVO",
    "direction.X+": "X+ · Izquierda → Derecha",
    "direction.X-": "X- · Derecha → Izquierda",
    "direction.Y+": "Y+ · Abajo → Arriba",
    "direction.Y-": "Y- · Arriba → Abajo",
    "results.title": "Resultados",
    "results.subtitle": "Dimensiones Findings independientes a partir de evidencia cuantitativa activa.",
    "settings.title": "Preferencias",
    "settings.subtitle": "Tema e idioma son preferencias de presentación — no evidencia Session.",
    "settings.theme": "Tema",
    "settings.locale": "Idioma",
    "theme.light": "Claro",
    "theme.dark": "Oscuro",
    "theme.system": "Seguir sistema",
    "unit.mm": "milímetros (mm)",
    "unit.cm": "centímetros (cm)",
    "unit.inch": "pulgadas (inch)",
    "finding.accuracy": "Exactitud",
    "finding.repeatability": "Repetibilidad",
    "finding.ratio": "Ratio",
    "finding.path_quality": "Calidad de trayectoria",
    "status.PASS": "Aprobado",
    "status.WARN": "Advertencia",
    "status.FAIL": "Fallido",
}

CATALOGS: dict[str, dict[str, str]] = {
    "en-US": _EN,
    "zh-TW": _ZH_TW,
    "zh-CN": _ZH_CN,
    "ja-JP": _JA,
    "ko-KR": _KO,
    "de-DE": _DE,
    "fr-FR": _FR,
    "es-ES": _ES,
}

# Core shell keys tracked for localization completeness (portfolio release target).
SHELL_REQUIRED_KEYS: tuple[str, ...] = (
    "app.title",
    "nav.setup",
    "nav.capture",
    "nav.results",
    "nav.settings",
    "setup.title",
    "setup.subtitle",
    "setup.vendor",
    "setup.model",
    "setup.notes",
    "setup.notes_deviations",
    "setup.distance",
    "setup.unit",
    "setup.apply",
    "setup.revert",
    "setup.applied",
    "setup.geometry",
    "setup.accuracy",
    "setup.accuracy.strict",
    "setup.accuracy.medium",
    "setup.accuracy.lenient",
    "setup.measurement_locked",
    "geometry.fixture_vector",
    "geometry.directional_axis",
    "capture.title",
    "capture.subtitle",
    "capture.start",
    "capture.admit_and_start",
    "capture.stop",
    "capture.cancel",
    "capture.admit",
    "capture.discard",
    "capture.configured_dpi",
    "capture.direction",
    "capture.physical_distance",
    "capture.instruction",
    "capture.lane.start",
    "capture.lane.target",
    "capture.focus_lost",
    "direction.X+",
    "direction.X-",
    "direction.Y+",
    "direction.Y-",
    "results.title",
    "results.subtitle",
    "settings.title",
    "settings.subtitle",
    "settings.theme",
    "settings.locale",
    "theme.light",
    "theme.dark",
    "theme.system",
    "unit.mm",
    "unit.cm",
    "unit.inch",
    "finding.accuracy",
    "finding.repeatability",
    "finding.ratio",
    "finding.path_quality",
    "status.PASS",
    "status.WARN",
    "status.FAIL",
)

# Native language names for locale combo display (not Session evidence).
LOCALE_DISPLAY_NAMES: dict[str, str] = {
    "en-US": "English",
    "zh-TW": "繁體中文",
    "zh-CN": "简体中文",
    "ja-JP": "日本語",
    "ko-KR": "한국어",
    "de-DE": "Deutsch",
    "fr-FR": "Français",
    "es-ES": "Español",
}
