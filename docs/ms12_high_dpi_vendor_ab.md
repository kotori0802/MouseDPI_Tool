"""High-DPI characterization — vendor-software A/B methodology (MS-1.2).

Descriptive experiment plan only. The Tool records condition metadata; it does
not conclude which condition is superior.
"""

# Condition A — controlled
# - Apply DPI/profile in a controlled manner
# - Vendor UI closed when practical
# - Prefer stable onboard profile
# - Record control_software_state (not_running / background_service_present / unknown)
# - Record dpi_configuration_source (onboard_profile / hardware_control / …)

# Condition B — vendor software operating normally
# - Same DUT, surface, fixture/contact, physical distance, DPI list, direction balance
# - control_software_state = ui_open (or background_service_present as observed)
# - control_software_name / version free text when known

# First characterization DPI set (balanced n≥10/DPI/condition when practical):
#   6400, 9600, 12750, 26000
#
# Prefer interleaved / counterbalanced ordering rather than completing one entire
# DPI block before the next when studying drift.
#
# Keep Relative DPI Scaling for localizing unusual relative scale between groups.
# Do not promote Ratio to native-capability or firmware-scaling verdicts.
#
# Fixture / measurement-system uncertainty notes are descriptive only —
# never auto-subtracted from CPI error or used to widen PASS thresholds.
