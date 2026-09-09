"""Engineering chart cards for DPI Behavior Trends (presentation only)."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.reporting.chart_cards import (
    ChartCardModel,
    ChartSeriesPoint,
    build_v1_chart_cards,
    format_observation_en,
)
from mouse_dpi_tool.ui.help_content import CHART_CUE_KEYS
from mouse_dpi_tool.ui.theme.tokens import ThemeTokens


def _nice_ticks(lo: float, hi: float, count: int = 4) -> list[float]:
    if hi <= lo:
        return [lo]
    span = hi - lo
    step = span / max(1, count)
    # Round step to 1/2/5 * 10^n
    import math

    exp = math.floor(math.log10(step)) if step > 0 else 0
    base = step / (10**exp)
    if base <= 1:
        nice = 1.0
    elif base <= 2:
        nice = 2.0
    elif base <= 5:
        nice = 5.0
    else:
        nice = 10.0
    step = nice * (10**exp)
    start = math.floor(lo / step) * step
    ticks: list[float] = []
    v = start
    while v <= hi + step * 0.01:
        if v >= lo - step * 0.01:
            ticks.append(v)
        v += step
        if len(ticks) > 12:
            break
    return ticks or [lo, hi]


class _PlotCanvas(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._card: ChartCardModel | None = None
        self._tokens: ThemeTokens | None = None
        self._hit: list[tuple[QPointF, ChartSeriesPoint]] = []
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)

    def set_card(self, card: ChartCardModel) -> None:
        self._card = card
        self.update()

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self._tokens = tokens
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._hit or self._card is None:
            return
        pos = event.position()
        best = None
        best_d = 14.0
        for pt, series in self._hit:
            d = (pt.x() - pos.x()) ** 2 + (pt.y() - pos.y()) ** 2
            if d < best_d * best_d:
                best_d = d**0.5
                best = series
        if best is not None:
            QToolTip.showText(event.globalPosition().toPoint(), self._card.point_tooltip_en(best), self)
        else:
            QToolTip.hideText()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tok = self._tokens
        bg = QColor(tok.surface if tok else "#FFFFFF")
        grid = QColor(tok.border if tok else "#D2D2D7")
        text = QColor(tok.text_secondary if tok else "#6E6E73")
        accent = QColor(tok.accent if tok else "#0071E3")
        plot_bg = QColor(tok.background if tok else "#F5F5F7")
        success = QColor(tok.success if tok else "#1F8F4E")
        danger = QColor(tok.danger if tok else "#C9342D")
        warn = QColor(tok.warning if tok else "#FFD60A")
        muted = QColor(tok.text_tertiary if tok else "#8E8E93")
        p.fillRect(self.rect(), bg)
        self._hit = []

        card = self._card
        if card is None or not card.points:
            p.setPen(QPen(text))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No group data")
            return

        pad_l, pad_r, pad_t, pad_b = 58, 18, 12, 40
        plot = QRectF(pad_l, pad_t, self.width() - pad_l - pad_r, self.height() - pad_t - pad_b)
        p.fillRect(plot, plot_bg)
        p.setPen(QPen(grid, 1))
        p.drawRect(plot)

        points = card.as_xy()
        xs = [a for a, _ in points]
        ys = [b for _, b in points]
        if card.ideal_points:
            xs = xs + [pt.configured_dpi for pt in card.ideal_points]
            ys = ys + [pt.value for pt in card.ideal_points]
        if card.thresholds is not None:
            ys = ys + [card.thresholds.pass_pct, card.thresholds.fail_pct, 0.0]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        if x1 <= x0:
            x1 = x0 + 1.0
        if y1 <= y0:
            y1 = y0 + 1.0
        x_pad = (x1 - x0) * 0.05
        y_pad = (y1 - y0) * 0.10
        x0 -= x_pad
        x1 += x_pad
        if card.thresholds is not None:
            y0 = min(0.0, y0 - y_pad)
        else:
            y0 -= y_pad
        y1 += y_pad

        def sx(x: float) -> float:
            return plot.left() + (x - x0) / (x1 - x0) * plot.width()

        def sy(y: float) -> float:
            return plot.bottom() - (y - y0) / (y1 - y0) * plot.height()

        # Y-axis ticks
        p.setPen(QPen(text))
        for tick in _nice_ticks(y0, y1, count=4):
            yy = sy(tick)
            if yy < plot.top() or yy > plot.bottom():
                continue
            p.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(plot.left(), yy), QPointF(plot.right(), yy))
            p.setPen(QPen(text))
            label = f"{tick:.0f}" if abs(tick) >= 10 else f"{tick:.2g}"
            p.drawText(
                QRectF(2, yy - 8, pad_l - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        if card.thresholds is not None:
            yp = card.thresholds.pass_pct
            yf = card.thresholds.fail_pct
            top = min(sy(yp), sy(yf))
            bot = max(sy(yp), sy(yf))
            band = QColor(warn)
            band.setAlpha(28)
            p.fillRect(QRectF(plot.left(), top, plot.width(), bot - top), band)
            p.setPen(QPen(success, 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), sy(yp)), QPointF(plot.right(), sy(yp)))
            p.setPen(QPen(danger, 1.2, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), sy(yf)), QPointF(plot.right(), sy(yf)))
            p.setPen(QPen(success))
            p.drawText(
                QRectF(plot.left() + 4, sy(yp) - 14, plot.width() - 8, 14),
                Qt.AlignmentFlag.AlignLeft,
                f"PASS ≤ {card.thresholds.pass_pct:g}%",
            )
            p.setPen(QPen(danger))
            p.drawText(
                QRectF(plot.left() + 4, sy(yf) - 14, plot.width() - 8, 14),
                Qt.AlignmentFlag.AlignLeft,
                f"FAIL > {card.thresholds.fail_pct:g}%",
            )
            p.setPen(QPen(QColor(tok.warning if tok else "#B26A00")))
            mid = (yp + yf) / 2
            p.drawText(
                QRectF(plot.left() + 4, sy(mid) - 7, plot.width() - 8, 14),
                Qt.AlignmentFlag.AlignLeft,
                f"WARN {card.thresholds.pass_pct:g}–{card.thresholds.fail_pct:g}%",
            )

        if card.ideal_points:
            lo = min(pt.configured_dpi for pt in card.ideal_points)
            hi = max(pt.configured_dpi for pt in card.ideal_points)
            p.setPen(QPen(muted, 1.4, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(sx(lo), sy(lo)), QPointF(sx(hi), sy(hi)))

        p.setPen(QPen(accent, 2.4))
        for i in range(1, len(points)):
            a, b = points[i - 1], points[i]
            p.drawLine(QPointF(sx(a[0]), sy(a[1])), QPointF(sx(b[0]), sy(b[1])))
        p.setBrush(accent)
        for series_pt, (x, y) in zip(card.points, points, strict=True):
            qpt = QPointF(sx(x), sy(y))
            p.drawEllipse(qpt, 3.5, 3.5)
            self._hit.append((qpt, series_pt))

        p.setPen(QPen(text))
        for x, _ in points:
            label = str(int(x)) if float(x).is_integer() else f"{x:g}"
            p.drawText(
                QRectF(sx(x) - 28, plot.bottom() + 4, 56, 18),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )


class _ChartCard(QFrame):
    def __init__(self, chart_id: str, parent=None) -> None:
        super().__init__(parent)
        self.chart_id = chart_id
        self.setObjectName("Card")
        self.title = QLabel()
        self.title.setObjectName("SectionTitle")
        self.title.setWordWrap(True)
        self.cue = QLabel()
        self.cue.setObjectName("Muted")
        self.cue.setWordWrap(True)
        self.caption = QLabel()
        self.caption.setObjectName("Hint")
        self.caption.setWordWrap(True)
        self.caption.setVisible(False)
        self.help_btn = QToolButton()
        self.help_btn.setObjectName("TechToggle")
        self.help_btn.setText("ⓘ")
        self.help_btn.setCheckable(True)
        self.help_btn.toggled.connect(self.caption.setVisible)
        self.legend = QLabel()
        self.legend.setObjectName("Hint")
        self.legend.setWordWrap(True)
        self.obs = QLabel()
        self.obs.setObjectName("Muted")
        self.obs.setWordWrap(True)
        self.note = QLabel()
        self.note.setObjectName("Hint")
        self.note.setWordWrap(True)
        self.x_label = QLabel()
        self.x_label.setObjectName("Hint")
        self.y_label = QLabel()
        self.y_label.setObjectName("Hint")
        self.plot = _PlotCanvas()

        head = QHBoxLayout()
        head.addWidget(self.title, 1)
        head.addWidget(self.help_btn, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)
        layout.addLayout(head)
        layout.addWidget(self.cue)
        layout.addWidget(self.caption)
        layout.addWidget(self.y_label)
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.x_label)
        layout.addWidget(self.legend)
        layout.addWidget(self.obs)
        layout.addWidget(self.note)

    def set_model(self, card: ChartCardModel, *, localize: Callable[[str], str] | None = None) -> None:
        t = localize or (lambda s: s)
        title_key = f"charts.{card.chart_id}.title"
        cap_key = f"charts.{card.chart_id}.caption"
        cue_key = CHART_CUE_KEYS.get(card.chart_id, "")
        title = t(title_key)
        caption = t(cap_key)
        self.title.setText(title if title != title_key else card.title_en)
        self.caption.setText(caption if caption != cap_key else card.caption_en)
        if cue_key:
            cue = t(cue_key)
            self.cue.setText(cue if cue != cue_key else "")
        self.help_btn.setToolTip(t("charts.how_to_read"))
        x_key, y_key = f"charts.{card.chart_id}.x", f"charts.{card.chart_id}.y"
        xl, yl = t(x_key), t(y_key)
        self.x_label.setText(xl if xl != x_key else card.x_label_en)
        self.y_label.setText(yl if yl != y_key else card.y_label_en)
        self.legend.setText(" · ".join(card.legend_en))
        legend_key = f"charts.{card.chart_id}.legend"
        legend = t(legend_key)
        if legend != legend_key:
            self.legend.setText(legend)
        else:
            self.legend.setText(" · ".join(card.legend_en))
        obs_key = f"charts.obs.{card.observation.code}" if card.observation else ""
        if card.observation and obs_key:
            localized = t(obs_key)
            if localized != obs_key:
                try:
                    self.obs.setText(localized.format(**card.observation.params))
                except (KeyError, ValueError):
                    self.obs.setText(format_observation_en(card.observation))
            else:
                self.obs.setText(format_observation_en(card.observation))
        else:
            self.obs.setText(format_observation_en(card.observation))
        note_key = f"charts.{card.chart_id}.metric_note"
        note = t(note_key)
        self.note.setText(note if note != note_key else (card.metric_note_en or ""))
        self.note.setVisible(bool(self.note.text()))
        self.plot.set_card(card)

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self.plot.apply_tokens(tokens)


class DpiTrendCharts(QWidget):
    """Three V1 engineering chart cards from Session group_summaries + settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._localize: Callable[[str], str] | None = None
        self.cards = {
            "measured_cpi": _ChartCard("measured_cpi"),
            "max_error": _ChartCard("max_error"),
            "repeatability": _ChartCard("repeatability"),
        }
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for key in ("measured_cpi", "max_error", "repeatability"):
            layout.addWidget(self.cards[key])

    def set_localize(self, localize: Callable[[str], str]) -> None:
        self._localize = localize

    def set_from_session(
        self,
        groups: Sequence[Mapping[str, Any]],
        settings: Mapping[str, Any],
    ) -> dict[str, ChartCardModel]:
        models = build_v1_chart_cards(groups, settings)
        for key, card in self.cards.items():
            card.set_model(models[key], localize=self._localize)
        return models

    def set_group_summaries(self, groups: Sequence[Mapping[str, Any]]) -> None:
        self.set_from_session(groups, {})

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        for card in self.cards.values():
            card.apply_tokens(tokens)
