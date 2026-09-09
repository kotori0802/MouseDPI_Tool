"""User Guide dialog — offline, presentation-only."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.ui.controllers import AppController
from mouse_dpi_tool.ui.help_content import guide_section_keys
from mouse_dpi_tool.ui.layout_metrics import (
    USER_GUIDE_DEFAULT_HEIGHT,
    USER_GUIDE_DEFAULT_WIDTH,
    USER_GUIDE_MIN_HEIGHT,
    USER_GUIDE_MIN_WIDTH,
)


class UserGuideDialog(QDialog):
    def __init__(self, controller: AppController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle(controller.i18n.t("help.guide.title"))
        self.setMinimumSize(USER_GUIDE_MIN_WIDTH, USER_GUIDE_MIN_HEIGHT)
        self.resize(USER_GUIDE_DEFAULT_WIDTH, USER_GUIDE_DEFAULT_HEIGHT)
        self.setModal(True)

        self.title = QLabel()
        self.title.setObjectName("HeroTitle")
        self.body_host = QVBoxLayout()
        self.body_host.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        self._scroll = scroll
        inner = QWidget()
        inner_l = QVBoxLayout(inner)
        inner_l.addWidget(self.title)
        inner_l.addLayout(self.body_host)
        inner_l.addStretch(1)
        scroll.setWidget(inner)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close is not None:
            close.clicked.connect(self.accept)

        root = QVBoxLayout(self)
        root.addWidget(scroll, 1)
        root.addWidget(buttons)
        self.retranslate()

    def retranslate(self) -> None:
        t = self.controller.i18n.t
        self.setWindowTitle(t("help.guide.title"))
        self.title.setText(t("help.guide.title"))
        while self.body_host.count():
            item = self.body_host.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        for title_key, body_key in guide_section_keys():
            section_title = QLabel(t(title_key))
            section_title.setObjectName("SectionTitle")
            section_title.setWordWrap(True)
            section_body = QLabel(t(body_key))
            section_body.setObjectName("Muted")
            section_body.setWordWrap(True)
            section_body.setTextFormat(Qt.TextFormat.RichText)
            self.body_host.addWidget(section_title)
            self.body_host.addWidget(section_body)
