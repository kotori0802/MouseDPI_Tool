"""Capture action bar — stacked presentation from CaptureActionBarMode.

Switch QStackedLayout only when mode changes (not every 33 ms live tick).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.ui.capture_transaction import CaptureActionBarMode


class CaptureActionBar(QWidget):
    """Stable stacked action chrome for Capture."""

    start_clicked = Signal()
    stop_clicked = Signal()
    cancel_clicked = Signal()
    admit_clicked = Signal()
    discard_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CaptureActionBar")
        self._mode = CaptureActionBarMode.IDLE

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.starting_label = QLabel()
        self.starting_label.setObjectName("Muted")
        self.stop_btn = QPushButton()
        self.cancel_btn = QPushButton()
        self.processing_label = QLabel()
        self.processing_label.setObjectName("Muted")
        self.admit_btn = QPushButton()
        self.admit_btn.setObjectName("PrimaryButton")
        self.discard_btn = QPushButton()
        self.discard_only_btn = QPushButton()

        for btn in (
            self.stop_btn,
            self.cancel_btn,
            self.admit_btn,
            self.discard_btn,
            self.discard_only_btn,
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.start_btn.clicked.connect(self.start_clicked.emit)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
        self.admit_btn.clicked.connect(self.admit_clicked.emit)
        self.discard_btn.clicked.connect(self.discard_clicked.emit)
        self.discard_only_btn.clicked.connect(self.discard_clicked.emit)

        idle = QWidget()
        idle.setObjectName("TransparentSurface")
        idle_l = QHBoxLayout(idle)
        idle_l.setContentsMargins(0, 0, 0, 0)
        idle_l.addWidget(self.start_btn)
        idle_l.addStretch(1)

        arming = QWidget()
        arming.setObjectName("TransparentSurface")
        arming_l = QHBoxLayout(arming)
        arming_l.setContentsMargins(0, 0, 0, 0)
        arming_l.addWidget(self.starting_label)
        arming_l.addStretch(1)

        running = QWidget()
        running.setObjectName("TransparentSurface")
        running_l = QHBoxLayout(running)
        running_l.setContentsMargins(0, 0, 0, 0)
        running_l.addWidget(self.stop_btn)
        running_l.addWidget(self.cancel_btn)
        running_l.addStretch(1)

        stopping = QWidget()
        stopping.setObjectName("TransparentSurface")
        stopping_l = QHBoxLayout(stopping)
        stopping_l.setContentsMargins(0, 0, 0, 0)
        stopping_l.addWidget(self.processing_label)
        stopping_l.addStretch(1)

        review = QWidget()
        review.setObjectName("TransparentSurface")
        review_l = QHBoxLayout(review)
        review_l.setContentsMargins(0, 0, 0, 0)
        review_l.addWidget(self.admit_btn)
        review_l.addWidget(self.discard_btn)
        review_l.addStretch(1)

        discard_only = QWidget()
        discard_only.setObjectName("TransparentSurface")
        discard_l = QHBoxLayout(discard_only)
        discard_l.setContentsMargins(0, 0, 0, 0)
        discard_l.addWidget(self.discard_only_btn)
        discard_l.addStretch(1)

        self._stack = QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._pages = {
            CaptureActionBarMode.IDLE: 0,
            CaptureActionBarMode.ARMING: 1,
            CaptureActionBarMode.RUNNING: 2,
            CaptureActionBarMode.STOPPING: 3,
            CaptureActionBarMode.REVIEW_ADMITTABLE: 4,
            CaptureActionBarMode.REVIEW_DISCARD_ONLY: 5,
        }
        for page in (idle, arming, running, stopping, review, discard_only):
            page.setAutoFillBackground(False)
            page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self._stack.addWidget(page)

        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(self._stack)

    @property
    def mode(self) -> CaptureActionBarMode:
        return self._mode

    def set_mode(self, mode: CaptureActionBarMode) -> bool:
        """Switch stack page only when mode changes. Returns True if switched."""
        if mode is self._mode:
            return False
        self._mode = mode
        self._stack.setCurrentIndex(self._pages[mode])
        return True

    def retranslate(self, t) -> None:
        self.start_btn.setText(t("capture.start_f5"))
        self.starting_label.setText(t("capture.action.starting"))
        self.stop_btn.setText(t("capture.stop_f5"))
        self.cancel_btn.setText(t("capture.cancel_esc"))
        self.processing_label.setText(t("capture.action.processing"))
        self.admit_btn.setText(t("capture.admit_and_start_f5"))
        self.discard_btn.setText(t("capture.discard"))
        self.discard_only_btn.setText(t("capture.discard"))

    def set_busy_enabled(
        self,
        *,
        can_start: bool,
        can_stop: bool,
        can_admit: bool,
        can_discard: bool,
    ) -> None:
        self.start_btn.setEnabled(can_start)
        self.stop_btn.setEnabled(can_stop)
        self.cancel_btn.setEnabled(can_stop)
        self.admit_btn.setEnabled(can_admit)
        self.discard_btn.setEnabled(can_discard)
        self.discard_only_btn.setEnabled(can_discard)
