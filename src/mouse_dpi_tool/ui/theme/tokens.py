"""Semantic design tokens — Apple-inspired engineering aesthetic (not a macOS skin)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    background: str
    surface: str
    surface_elevated: str
    border: str
    text_primary: str
    text_secondary: str
    text_tertiary: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    button: str
    button_hover: str
    button_pressed: str
    success: str
    warning: str
    danger: str
    sidebar: str
    sidebar_active: str
    focus_ring: str
    font_ui: str
    font_mono: str
    radius_sm: int
    radius_md: int
    radius_lg: int
    space_md: int
    space_lg: int


LIGHT = ThemeTokens(
    name="light",
    background="#F5F5F7",
    surface="#FFFFFF",
    surface_elevated="#FBFBFD",
    border="#D2D2D7",
    text_primary="#1D1D1F",
    text_secondary="#6E6E73",
    text_tertiary="#8E8E93",
    accent="#0071E3",
    accent_hover="#0077ED",
    accent_pressed="#006EDB",
    accent_soft="#E8F1FC",
    button="#E8E8ED",
    button_hover="#DEDEE3",
    button_pressed="#D2D2D7",
    success="#1F8F4E",
    warning="#B26A00",
    danger="#C9342D",
    sidebar="#F0F0F2",
    sidebar_active="#FFFFFF",
    focus_ring="#0071E3",
    font_ui='"Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
    font_mono='"Cascadia Mono", "Consolas", "Courier New", monospace',
    radius_sm=8,
    radius_md=12,
    radius_lg=16,
    space_md=12,
    space_lg=20,
)

DARK = ThemeTokens(
    name="dark",
    background="#0D0D0F",
    surface="#1C1C1E",
    surface_elevated="#2C2C2E",
    border="#3A3A3C",
    text_primary="#F5F5F7",
    text_secondary="#C7C7CC",
    text_tertiary="#8E8E93",
    accent="#0A84FF",
    accent_hover="#409CFF",
    accent_pressed="#0071E3",
    accent_soft="#13253A",
    button="#2C2C2E",
    button_hover="#3A3A3C",
    button_pressed="#242426",
    success="#30D158",
    warning="#FFD60A",
    danger="#FF453A",
    sidebar="#111113",
    sidebar_active="#1C2A3A",
    focus_ring="#0A84FF",
    font_ui='"Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
    font_mono='"Cascadia Mono", "Consolas", "Courier New", monospace',
    radius_sm=8,
    radius_md=12,
    radius_lg=16,
    space_md=12,
    space_lg=20,
)


def tokens_for(theme: str, *, system_is_dark: bool = False) -> ThemeTokens:
    mode = str(theme or "system").lower()
    if mode == "system":
        mode = "dark" if system_is_dark else "light"
    return DARK if mode == "dark" else LIGHT


def stylesheet(tokens: ThemeTokens) -> str:
    """Phase 4 visual roles — Precision Engineering Workspace chrome.

    Selected ≠ Focus ≠ Primary. Labels/internal panels must not inherit a filled
    QWidget background (that caused empty-title strips and faux nested cards).
    """
    return f"""
    QMainWindow, QDialog {{
        background-color: {tokens.background};
        color: {tokens.text_primary};
        font-family: {tokens.font_ui};
        font-size: 14px;
    }}
    QWidget {{
        color: {tokens.text_primary};
        font-family: {tokens.font_ui};
        font-size: 14px;
        background-color: {tokens.background};
    }}
    /* Text and internal layout panels: no faux filled strips / nested cards. */
    QLabel {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QWidget#TransparentSurface {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QFrame#Card QWidget#TransparentSurface {{
        background-color: transparent;
        background: transparent;
    }}
    QStackedWidget, QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    QFrame#Sidebar {{
        background-color: {tokens.sidebar};
        border-right: 1px solid {tokens.border};
    }}
    QPushButton[class="NavButton"] {{
        text-align: left;
        padding: 10px 14px;
        border: 1px solid transparent;
        border-radius: {tokens.radius_md}px;
        color: {tokens.text_secondary};
        background: transparent;
    }}
    QPushButton[class="NavButton"]:hover {{
        background: {tokens.surface};
        color: {tokens.text_primary};
    }}
    QPushButton[class="NavButton"]:pressed {{
        background: {tokens.surface_elevated};
    }}
    QPushButton[class="NavButton"][active="true"] {{
        background: {tokens.accent_soft};
        color: {tokens.text_primary};
        font-weight: 600;
        border: 1px solid {tokens.border};
    }}
    QPushButton[class="NavButton"]:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QFrame#Card {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_lg}px;
        padding: 8px;
    }}
    QLabel#HeroTitle {{
        font-size: 28px;
        font-weight: 650;
        letter-spacing: -0.5px;
        color: {tokens.text_primary};
        background: transparent;
        border: none;
    }}
    QLabel#EmptyStateTitle {{
        font-size: 18px;
        font-weight: 600;
        letter-spacing: -0.2px;
        color: {tokens.text_primary};
        background-color: transparent;
        background: transparent;
        border: none;
        padding: 0px;
        margin: 0px;
    }}
    QLabel#SectionTitle {{
        font-size: 18px;
        font-weight: 600;
        letter-spacing: -0.2px;
        color: {tokens.text_primary};
        background-color: transparent;
        background: transparent;
        border: none;
        padding: 0px;
    }}
    QLabel#Muted {{
        color: {tokens.text_secondary};
        background: transparent;
        border: none;
    }}
    QLabel#FormLabel {{
        color: {tokens.text_secondary};
        background: transparent;
        border: none;
        padding: 0px;
        font-weight: 500;
    }}
    QLabel#FormGroupTitle {{
        color: {tokens.text_primary};
        background: transparent;
        border: none;
        padding: 0px 0px 2px 0px;
        font-size: 13px;
        font-weight: 600;
        letter-spacing: -0.1px;
    }}
    QLabel#CommittedSummary {{
        color: {tokens.text_primary};
        background: {tokens.surface_elevated};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_sm}px;
        padding: 10px 12px;
        font-weight: 500;
    }}
    QFrame#GeometryTile {{
        background: {tokens.surface_elevated};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_md}px;
    }}
    QFrame#GeometryTile:hover {{
        border-color: {tokens.text_tertiary};
        background: {tokens.surface};
    }}
    QFrame#GeometryTile[selected="true"] {{
        border: 1px solid {tokens.accent};
        background: {tokens.accent_soft};
    }}
    QFrame#GeometryTile:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QFrame#GeometryTile[selected="true"]:focus {{
        border: 2px solid {tokens.focus_ring};
        background: {tokens.accent_soft};
    }}
    QLabel#GeometryTileTitle {{
        color: {tokens.text_primary};
        font-weight: 600;
        background: transparent;
        border: none;
    }}
    QLabel#GeometryTileSubtitle {{
        color: {tokens.text_secondary};
        font-size: 12px;
        background: transparent;
        border: none;
    }}
    QLabel#Hint, QLabel#PassiveHelper {{
        color: {tokens.text_tertiary};
        font-size: 12px;
        background: transparent;
        border: none;
        padding: 0px;
    }}
    QLabel#PassiveHelper {{
        line-height: 1.35;
        padding-top: 2px;
        padding-bottom: 4px;
    }}
    QLabel#CaptureCommandHint {{
        color: {tokens.text_secondary};
        font-size: 12px;
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    /* Phase 4.1 / 4.2 — structural wrappers transparent; intentional surfaces explicit. */
    QFrame#CaptureShell {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_lg}px;
        padding: 0px;
    }}
    QFrame#CaptureHeader,
    QWidget#CaptureHeader {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QWidget#EvidenceCanvasHost {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QWidget#CaptureActionBar {{
        background-color: transparent;
        background: transparent;
        border: none;
        padding: 2px 0px;
    }}
    QWidget#CaptureActionBar QWidget#TransparentSurface {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QTabWidget#TrialTabs {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QTabWidget#TrialTabs QTabBar {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QTabWidget#TrialTabs::pane {{
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_sm}px;
        background: {tokens.surface};
        top: 6px;
        padding-top: 4px;
    }}
    QTabWidget#TrialTabs QTabBar::tab {{
        background: transparent;
        color: {tokens.text_secondary};
        padding: 8px 14px;
        border-radius: {tokens.radius_sm}px;
        margin-right: 4px;
        margin-bottom: 6px;
        border: 1px solid transparent;
    }}
    QTabWidget#TrialTabs QTabBar::tab:selected {{
        background: {tokens.surface_elevated};
        color: {tokens.text_primary};
        font-weight: 600;
        border: 1px solid {tokens.border};
    }}
    QTabWidget#TrialTabs QTabBar::tab:focus {{
        border: 2px solid {tokens.focus_ring};
    }}
    QWidget#TrialWorkspace {{
        background-color: transparent;
        background: transparent;
        border: none;
    }}
    QTableWidget#TrialTable {{
        background: {tokens.surface};
        alternate-background-color: {tokens.surface_elevated};
        gridline-color: {tokens.border};
        border: none;
        border-radius: {tokens.radius_sm}px;
        color: {tokens.text_primary};
    }}
    QTableWidget#TrialTable QHeaderView {{
        background: transparent;
    }}
    QTableWidget#TrialTable QTableCornerButton::section {{
        background: {tokens.surface_elevated};
        border: none;
    }}
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
        background: {tokens.surface_elevated};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_md}px;
        padding: 7px 12px;
        min-height: 30px;
        color: {tokens.text_primary};
        selection-background-color: {tokens.accent};
        selection-color: #FFFFFF;
    }}
    QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {tokens.text_tertiary};
    }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid {tokens.focus_ring};
        padding: 6px 11px;
    }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {tokens.text_tertiary};
        background: {tokens.surface};
        border: 1px solid {tokens.border};
    }}
    QSpinBox#DpiFineSpin {{
        padding: 7px 28px 7px 12px;
    }}
    QSpinBox#DpiFineSpin:focus {{
        padding: 6px 27px 6px 11px;
    }}
    QComboBox {{
        padding-right: 28px;
    }}
    QComboBox#DpiPresetCombo {{
        /* Width comes from layout_metrics content sizing — do not clamp. */
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 28px;
        border: none;
        border-left: 1px solid {tokens.border};
    }}
    QComboBox QAbstractItemView {{
        background: {tokens.surface_elevated};
        border: 1px solid {tokens.border};
        color: {tokens.text_primary};
        selection-background-color: {tokens.accent_soft};
        selection-color: {tokens.text_primary};
        outline: 0;
        padding: 4px;
    }}
    QPushButton {{
        background: {tokens.button};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_md}px;
        padding: 8px 16px;
        min-height: 20px;
        font-weight: 550;
    }}
    QPushButton:hover {{
        background: {tokens.button_hover};
    }}
    QPushButton:pressed {{
        background: {tokens.button_pressed};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        color: {tokens.text_tertiary};
        background: {tokens.surface};
        border: 1px solid {tokens.border};
    }}
    QPushButton:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QPushButton#PrimaryButton {{
        background: {tokens.accent};
        color: #FFFFFF;
        border: 1px solid {tokens.accent};
    }}
    QPushButton#PrimaryButton:hover {{
        background: {tokens.accent_hover};
        border-color: {tokens.accent_hover};
    }}
    QPushButton#PrimaryButton:pressed {{
        background: {tokens.accent_pressed};
        border-color: {tokens.accent_pressed};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton#PrimaryButton:disabled {{
        background: {tokens.button};
        color: {tokens.text_tertiary};
        border: 1px solid {tokens.border};
    }}
    QPushButton#PrimaryButton:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QPushButton#Segment {{
        border-radius: {tokens.radius_sm}px;
        padding: 8px 14px;
        background: transparent;
        border: 1px solid transparent;
        color: {tokens.text_secondary};
    }}
    QPushButton#Segment:hover {{
        background: {tokens.surface};
        color: {tokens.text_primary};
    }}
    QPushButton#Segment[selected="true"] {{
        background: {tokens.accent_soft};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
        font-weight: 600;
    }}
    QPushButton#Segment:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QFrame#SegmentGroup {{
        background: {tokens.button};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_md}px;
        padding: 3px;
    }}
    QLabel#PosterCpi {{
        font-size: 32px;
        font-weight: 700;
        letter-spacing: -0.8px;
        color: {tokens.text_primary};
        background: transparent;
    }}
    QLabel#ReadyBanner {{
        font-size: 22px;
        font-weight: 700;
        padding: 10px 14px;
        border-radius: {tokens.radius_md}px;
        background: {tokens.accent_soft};
        color: {tokens.text_primary};
        border: 1px solid {tokens.border};
    }}
    QFrame#TrialPoster {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_lg}px;
        margin-top: 4px;
    }}
    QFrame#TrialPoster[status="pass"] {{
        border-left: 4px solid {tokens.success};
    }}
    QFrame#TrialPoster[status="warn"] {{
        border-left: 4px solid {tokens.warning};
    }}
    QFrame#TrialPoster[status="fail"] {{
        border-left: 4px solid {tokens.danger};
    }}
    QToolButton#TechToggle {{
        border: 1px solid transparent;
        color: {tokens.text_secondary};
        padding: 4px 6px;
        background: transparent;
        border-radius: {tokens.radius_sm}px;
    }}
    QToolButton#TechToggle:hover {{
        background: {tokens.surface_elevated};
        color: {tokens.text_primary};
    }}
    QToolButton#TechToggle:focus {{
        border: 2px solid {tokens.focus_ring};
        outline: none;
    }}
    QFrame#TechPanel {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_md}px;
    }}
    QFrame#ResultPoster {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_lg}px;
        min-width: 220px;
        min-height: 140px;
    }}
    QFrame#ResultPoster[status="pass"] {{
        border-top: 3px solid {tokens.success};
    }}
    QFrame#ResultPoster[status="warn"] {{
        border-top: 3px solid {tokens.warning};
    }}
    QFrame#ResultPoster[status="fail"] {{
        border-top: 3px solid {tokens.danger};
    }}
    QFrame#ResultPoster[status="not_tested"],
    QFrame#ResultPoster[status="not_evaluated"] {{
        border-top: 3px solid {tokens.border};
    }}
    QFrame#ResultPosterSecondary {{
        background: {tokens.surface};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_lg}px;
        min-width: 220px;
        min-height: 120px;
    }}
    QFrame#ResultPosterSecondary[status="pass"] {{
        border-top: 2px solid {tokens.success};
    }}
    QFrame#ResultPosterSecondary[status="warn"] {{
        border-top: 2px solid {tokens.warning};
    }}
    QFrame#ResultPosterSecondary[status="fail"] {{
        border-top: 2px solid {tokens.danger};
    }}
    QFrame#ResultPosterSecondary[status="not_tested"],
    QFrame#ResultPosterSecondary[status="not_evaluated"] {{
        border-top: 2px solid {tokens.border};
    }}
    QLabel#FindingStatus {{
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.4px;
        background: transparent;
        border: none;
        padding: 2px 0px;
    }}
    QLabel#FindingStatus[secondary="true"] {{
        font-size: 18px;
        font-weight: 650;
    }}
    QLabel#FindingStatus[status="pass"] {{ color: {tokens.success}; }}
    QLabel#FindingStatus[status="warn"] {{ color: {tokens.warning}; }}
    QLabel#FindingStatus[status="fail"] {{ color: {tokens.danger}; }}
    QLabel#FindingStatus[status="not_tested"],
    QLabel#FindingStatus[status="not_evaluated"] {{ color: {tokens.text_tertiary}; }}
    QLabel#MetricKey {{
        color: {tokens.text_secondary};
        font-size: 13px;
        background: transparent;
    }}
    QLabel#MetricValue {{
        color: {tokens.text_primary};
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    }}
    QTableWidget {{
        background: {tokens.surface};
        alternate-background-color: {tokens.surface_elevated};
        gridline-color: {tokens.border};
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_sm}px;
        color: {tokens.text_primary};
    }}
    QHeaderView::section {{
        background: {tokens.surface_elevated};
        color: {tokens.text_secondary};
        border: none;
        border-bottom: 1px solid {tokens.border};
        padding: 8px;
        font-weight: 600;
    }}
    QTabWidget::pane {{
        border: 1px solid {tokens.border};
        border-radius: {tokens.radius_sm}px;
        background: {tokens.surface};
    }}
    QTabBar::tab {{
        background: transparent;
        color: {tokens.text_secondary};
        padding: 8px 14px;
        border-radius: {tokens.radius_sm}px;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{
        background: {tokens.surface_elevated};
        color: {tokens.text_primary};
        font-weight: 600;
    }}
    QStatusBar {{
        background: {tokens.surface};
        color: {tokens.text_secondary};
        border-top: 1px solid {tokens.border};
    }}
    """
