"""UI presentation boundary + invariance tests (no domain math in views)."""

from __future__ import annotations

from pathlib import Path

import pytest

from mouse_dpi_tool.session import Session
from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.i18n import I18n
from mouse_dpi_tool.ui.preferences import load_preferences, save_preferences
from mouse_dpi_tool.ui.theme import ThemeManager
from mouse_dpi_tool.ui.viewmodels import build_results_viewmodel


def _perfect_counts(dpi: int, distance_mm: float = 100.0) -> int:
    return int(round(dpi * (distance_mm / 25.4)))


def _fixed_session() -> Session:
    session = Session(
        dut={"vendor": "ExampleVendor", "model": "DemoMouse", "notes": ""},
        measurement_context={"method": "synthetic", "direction": "X+"},
        settings={"distance_mm": 100.0, "distance_unit": "mm", "min_valid_trials_per_group": 1},
        session_id="mds_ui_invariance",
        created_at="2026-09-03T14:00:00+08:00",
    )
    session.add_synthetic_trial(configured_dpi=800, counts_x=_perfect_counts(800))
    session.add_synthetic_trial(configured_dpi=1600, counts_x=_perfect_counts(1600))
    session.set_manual_observation("dpi_indicator_check", status="PASS")
    return session


def test_ui0a_path_quality_pass_plus_not_evaluated_is_warn():
    session = Session(
        settings={"distance_mm": 100.0, "min_valid_trials_per_group": 1},
        measurement_context={"method": "synthetic"},
    )
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 3150.0,
            "straightness_pct": 100.0,
            "status": "PASS",
            "issue_codes": [],
            "fixture_noise_floor_counts": 7,
        },
    )
    session.add_synthetic_trial(
        configured_dpi=800,
        counts_x=_perfect_counts(800),
        path_quality_snapshot={
            "path_total_counts": 0.0,
            "straightness_pct": 0.0,
            "status": "NOT_EVALUATED",
            "issue_codes": ["NO_PATH_EVIDENCE_ABOVE_NOISE_FLOOR"],
            "fixture_noise_floor_counts": 7,
        },
    )
    finding = session.to_session_dict()["findings"]["path_quality"]
    assert finding["status"] == "WARN"
    assert "PATH_QUALITY_COVERAGE_INCOMPLETE" in finding["issue_codes"]


def test_manual_observation_uses_canonical_template_label_not_ui_text():
    session = Session(settings={"distance_mm": 100.0}, measurement_context={"method": "synthetic"})
    row = session.set_manual_observation("dpi_indicator_check", status="PASS", notes="ok")
    assert row["id"] == "dpi_indicator_check"
    assert row["label"] == "DPI Indicator Check"
    assert "指示" not in row["label"]


def test_controller_never_persists_localized_manual_labels():
    controller = AppController(preferences={"theme": "light", "locale": "ja-JP"})
    controller.set_manual_observation("dpi_indicator_check", status="PASS")
    snap = controller.session_snapshot()
    assert snap["findings"]["manual_observations"][0]["id"] == "dpi_indicator_check"
    assert snap["findings"]["manual_observations"][0]["label"] == "DPI Indicator Check"


def test_controller_passes_canonical_units_only():
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.update_distance(distance_input=10.0, unit="centimeters")
    assert controller.session.settings["distance_unit"] == "cm"
    assert controller.session.settings["distance_mm"] == pytest.approx(100.0)


def test_presentation_invariance_across_theme_and_locale(tmp_path: Path):
    session = _fixed_session()
    evidence = session.to_session_dict()
    fingerprints = []
    display_titles = []
    for theme, locale in (
        ("light", "en-US"),
        ("dark", "ja-JP"),
        ("light", "de-DE"),
    ):
        prefs_path = tmp_path / f"prefs_{theme}_{locale}.json"
        save_preferences({"theme": theme, "locale": locale}, prefs_path)
        prefs = load_preferences(prefs_path)
        i18n = I18n(prefs["locale"])
        theme_mgr = ThemeManager(prefs["theme"])
        vm = build_results_viewmodel(evidence, i18n)
        fingerprints.append(vm.evidence_fingerprint)
        display_titles.append(tuple(card.title for card in vm.finding_cards))
        assert theme_mgr.tokens.name in {"light", "dark"}
        # Domain evidence unchanged by presentation plumbing.
        assert session.to_session_dict()["findings"] == evidence["findings"]
        assert session.to_session_dict()["trials"] == evidence["trials"]

    assert fingerprints[0] == fingerprints[1] == fingerprints[2]
    # Localized titles should differ for at least one dimension across locales.
    assert display_titles[0] != display_titles[1]


def test_no_pyside_imports_in_domain_packages():
    root = Path(__file__).resolve().parents[2] / "src" / "mouse_dpi_tool"
    offenders: list[str] = []
    for package in ("measurement", "capture", "path_quality", "session", "findings"):
        for path in (root / package).rglob("*.py"):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "import PySide6" in line or "from PySide6" in line or "import PyQt" in line or "from PyQt" in line:
                    offenders.append(f"{path.relative_to(root)}:{i}:{stripped}")
    assert offenders == []


def test_distance_unit_change_preserves_physical_mm():
    """Unit-only changes must keep canonical distance_mm (100 mm ↔ 10 cm ↔ ~3.937 inch)."""
    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.update_distance(distance_input=100.0, unit="mm")
    assert controller.session.settings["distance_mm"] == pytest.approx(100.0)

    cm = controller.change_distance_unit_preserving_physical("cm")
    assert cm["distance_mm"] == pytest.approx(100.0)
    assert cm["distance_unit"] == "cm"
    assert cm["distance_input"] == pytest.approx(10.0)

    inch = controller.change_distance_unit_preserving_physical("inch")
    assert inch["distance_mm"] == pytest.approx(100.0)
    assert inch["distance_unit"] == "inch"
    assert inch["distance_input"] == pytest.approx(100.0 / 25.4)

    back = controller.change_distance_unit_preserving_physical("mm")
    assert back["distance_mm"] == pytest.approx(100.0)
    assert back["distance_input"] == pytest.approx(100.0)

    # Pure display conversion helper used by Setup UI spinbox.
    assert controller.convert_distance_display(100.0, from_unit="mm", to_unit="cm") == pytest.approx(10.0)
    assert controller.convert_distance_display(10.0, from_unit="cm", to_unit="inch") == pytest.approx(100.0 / 25.4)


def test_shell_required_keys_english_complete():
    from mouse_dpi_tool.ui.i18n import CATALOGS, SHELL_REQUIRED_KEYS

    missing = [key for key in SHELL_REQUIRED_KEYS if key not in CATALOGS["en-US"]]
    assert missing == []


def test_shell_required_keys_resolve_in_all_locales():
    from mouse_dpi_tool.ui import SUPPORTED_LOCALES
    from mouse_dpi_tool.ui.i18n import SHELL_REQUIRED_KEYS

    for locale in SUPPORTED_LOCALES:
        i18n = I18n(locale)
        for key in SHELL_REQUIRED_KEYS:
            text = i18n.t(key)
            assert text, f"{locale}:{key} empty"
            assert text != key, f"{locale}:{key} fell through to raw key"


def test_shell_i18n_gap_inventory_and_critical_translations():
    """Track incomplete catalogs; critical UX keys must already differ from English."""
    from mouse_dpi_tool.ui import SUPPORTED_LOCALES
    from mouse_dpi_tool.ui.i18n import shell_i18n_gaps

    gaps = shell_i18n_gaps()
    assert set(gaps) == set(SUPPORTED_LOCALES) - {"en-US"}
    # Cognates that legitimately match English (e.g. FR "Capture") are excluded.
    critical = (
        "app.title",
        "nav.setup",
        "nav.results",
        "nav.settings",
        "setup.apply",
        "capture.admit",
        "capture.direction",
        "direction.X+",
        "theme.light",
        "theme.dark",
        "theme.system",
        "finding.accuracy",
        "status.PASS",
        "status.FAIL",
    )
    for locale, missing in gaps.items():
        still = [key for key in critical if key in missing]
        assert still == [], f"{locale} still falling back to English for: {still}"


def test_theme_system_follows_os_flag():
    light = ThemeManager("system", system_is_dark=False)
    dark = ThemeManager("system", system_is_dark=True)
    assert light.tokens.name == "light"
    assert dark.tokens.name == "dark"
    mgr = ThemeManager("system", system_is_dark=False)
    mgr.set_system_is_dark(True)
    assert mgr.tokens.name == "dark"


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_setup_unit_combo_keeps_number_and_updates_physical_mm(qapp):
    """Unit change reinterprets the typed number; preview shows canonical mm."""
    from mouse_dpi_tool.ui.components.combo import combo_data
    from mouse_dpi_tool.ui.views.pages import SetupPage

    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    controller.update_distance(distance_input=100.0, unit="mm")
    page = SetupPage(controller)
    assert page.distance.value() == pytest.approx(100.0)
    assert combo_data(page.unit) == "mm"
    assert "100" in page.distance_mm_preview.text()

    idx = page.unit.findData("cm")
    assert idx >= 0
    page.unit.setCurrentIndex(idx)
    assert combo_data(page.unit) == "cm"
    # Number kept; 100 cm = 1000 mm physical.
    assert page.distance.value() == pytest.approx(100.0)
    assert "1000" in page.distance_mm_preview.text().replace(",", "")

    page.distance.setValue(2.0)
    idx = page.unit.findData("inch")
    page.unit.setCurrentIndex(idx)
    assert page.distance.value() == pytest.approx(2.0)
    assert "50.8" in page.distance_mm_preview.text().replace(",", "")

    page._apply()
    assert controller.session.settings["distance_mm"] == pytest.approx(50.8)
    assert controller.session.settings["distance_unit"] == "inch"


def test_results_refresh_on_navigate_after_session_change(qapp):
    from mouse_dpi_tool.ui.views import MainWindow

    controller = AppController(preferences={"theme": "light", "locale": "en-US"})
    window = MainWindow(controller)
    window._navigate("results")
    before_fp = controller.results_viewmodel().evidence_fingerprint

    controller.session = _fixed_session()
    # Stale cards would still reflect the empty session until navigate→refresh.
    window._navigate("setup")
    window._navigate("results")
    after_vm = controller.results_viewmodel()
    assert after_vm.evidence_fingerprint != before_fp
    assert any(card.canonical_status == "PASS" for card in after_vm.finding_cards)
    assert window.results_page.v1_host.count() >= 4


def test_combo_display_labels_use_item_data_not_text(qapp):
    from mouse_dpi_tool.ui.components.combo import combo_data
    from mouse_dpi_tool.ui.views.pages import SettingsPage

    controller = AppController(preferences={"theme": "system", "locale": "zh-TW"})
    page = SettingsPage(controller, on_prefs_changed=lambda: None)
    assert str(controller.preferences.get("theme")) == "system"
    assert page._theme_buttons["system"].property("selected") == "true"
    assert combo_data(page.locale) == "zh-TW"
    assert page.locale.currentText() == "繁體中文"

    controller.set_locale("ja-JP")
    page.retranslate()
    assert combo_data(page.locale) == "ja-JP"
    assert str(controller.preferences.get("theme")) == "system"


def _synth_engine_factory(samples):
    from mouse_dpi_tool.capture import CaptureEngine, SyntheticEventSource

    def factory(*, on_status=None):
        return CaptureEngine(source=SyntheticEventSource(samples), on_status=on_status)

    return factory


def test_controller_capture_start_stop_admit_with_path_quality():
    from mouse_dpi_tool.contracts.movement import MovementSample

    samples = [MovementSample(dx=3150, dy=0, device_id="synth")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_synth_engine_factory(samples),
    )
    controller.set_configured_dpi(800)
    controller.start_capture()
    assert controller._engine is not None
    controller._engine.wait_until_idle()
    assert controller.capture_viewmodel().state == "running"
    assert controller.capture_viewmodel().net_counts_x == 3150
    controller.stop_capture()
    vm = controller.capture_viewmodel()
    assert vm.is_valid_complete_capture is True
    assert vm.can_admit is True
    assert vm.path_quality_status in {"PASS", "WARN", "FAIL", "NOT_EVALUATED"}

    trial = controller.admit_capture()
    assert trial["trial_id"] == 1
    assert trial["accepted"] is True
    assert "measured_cpi" in trial
    assert controller.capture_viewmodel().can_admit is False
    assert len(controller.session.active_trials) == 1
    # Findings rebuilt by Session — not by UI.
    snap = controller.session_snapshot()
    assert "accuracy" in snap["findings"]


def test_controller_cancel_discards_nets():
    from mouse_dpi_tool.contracts.movement import MovementSample

    samples = [MovementSample(dx=100, dy=0, device_id="synth")]
    controller = AppController(
        preferences={"theme": "light", "locale": "en-US"},
        engine_factory=_synth_engine_factory(samples),
    )
    controller.start_capture()
    assert controller._engine is not None
    controller._engine.wait_until_idle()
    controller.cancel_capture()
    vm = controller.capture_viewmodel()
    assert vm.state == "cancelled"
    assert vm.net_counts_x == 0
    assert vm.can_admit is False
