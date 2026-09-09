"""Engineering diagnostics charts (Trial sequence / distribution / speed).

Presentation only — built from canonical Session trials. Never Findings.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mouse_dpi_tool.reporting.trial_diagnostics import (
    build_dpi_error_distributions,
    build_latency_error_points,
    build_speed_correlations,
    build_speed_error_points,
    build_trial_sequence_points,
    session_has_motion_timing,
)
from mouse_dpi_tool.ui.theme.tokens import ThemeTokens


class _ScatterCanvas(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._points: list[tuple[float, float, str]] = []
        self._xlabel = ""
        self._ylabel = ""
        self._title = ""
        self._tokens: ThemeTokens | None = None
        self._box_rows: list[dict[str, Any]] = []
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_scatter(
        self,
        points: Sequence[tuple[float, float, str]],
        *,
        title: str,
        xlabel: str,
        ylabel: str,
    ) -> None:
        self._points = list(points)
        self._box_rows = []
        self._title = title
        self._xlabel = xlabel
        self._ylabel = ylabel
        self.update()

    def set_box(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        title: str,
        ylabel: str,
    ) -> None:
        self._box_rows = [dict(r) for r in rows]
        self._points = []
        self._title = title
        self._xlabel = "Configured DPI"
        self._ylabel = ylabel
        self.update()

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self._tokens = tokens
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        tok = self._tokens
        bg = QColor(tok.surface if tok else "#FFFFFF")
        ink = QColor(tok.text_primary if tok else "#1d1d1f")
        muted = QColor(tok.text_secondary if tok else "#6e6e73")
        accent = QColor(tok.accent if tok else "#0071e3")
        p.fillRect(self.rect(), bg)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 52, 16, 28, 40
        plot = QRectF(pad_l, pad_t, max(1, w - pad_l - pad_r), max(1, h - pad_t - pad_b))
        p.setPen(QPen(muted, 1))
        p.drawRect(plot)
        p.setPen(ink)
        p.drawText(QRectF(0, 4, w, 20), Qt.AlignmentFlag.AlignHCenter, self._title)
        p.setPen(muted)
        p.drawText(QRectF(0, h - 22, w, 18), Qt.AlignmentFlag.AlignHCenter, self._xlabel)

        if self._box_rows:
            self._paint_boxes(p, plot, ink, muted, accent)
            return
        if not self._points:
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter, "No data")
            return
        xs = [a for a, _, _ in self._points]
        ys = [b for _, b, _ in self._points]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        if abs(xmax - xmin) < 1e-9:
            xmax = xmin + 1
        if abs(ymax - ymin) < 1e-9:
            ymax = ymin + 1
        # pad y
        ypad = (ymax - ymin) * 0.08
        ymin -= ypad
        ymax += ypad

        def map_pt(x: float, y: float) -> QPointF:
            nx = (x - xmin) / (xmax - xmin)
            ny = (y - ymin) / (ymax - ymin)
            return QPointF(plot.left() + nx * plot.width(), plot.bottom() - ny * plot.height())

        # zero line if in range
        if ymin <= 0 <= ymax:
            z = map_pt(xmin, 0)
            p.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), z.y()), QPointF(plot.right(), z.y()))

        palette = [accent, QColor("#34c759"), QColor("#ff9f0a"), QColor("#af52de"), QColor("#ff375f")]
        dpi_colors: dict[str, QColor] = {}
        for x, y, label in self._points:
            if label not in dpi_colors:
                dpi_colors[label] = palette[len(dpi_colors) % len(palette)]
            p.setBrush(dpi_colors[label])
            p.setPen(Qt.PenStyle.NoPen)
            pt = map_pt(x, y)
            p.drawEllipse(pt, 3.5, 3.5)
        p.setPen(muted)
        p.drawText(QRectF(2, pad_t, pad_l - 4, plot.height()), Qt.AlignmentFlag.AlignVCenter, self._ylabel)

    def _paint_boxes(self, p: QPainter, plot: QRectF, ink, muted, accent) -> None:
        rows = self._box_rows
        if not rows:
            return
        n = len(rows)
        slot = plot.width() / max(1, n)
        all_y: list[float] = []
        for r in rows:
            for key in ("min_error_pct", "q1_error_pct", "median_error_pct", "q3_error_pct", "max_error_pct"):
                if r.get(key) is not None:
                    all_y.append(float(r[key]))
            all_y.extend(float(e) for e in (r.get("errors") or []))
        if not all_y:
            return
        ymin, ymax = min(all_y), max(all_y)
        if abs(ymax - ymin) < 1e-9:
            ymax = ymin + 1
        ypad = (ymax - ymin) * 0.1
        ymin -= ypad
        ymax += ypad

        def my(y: float) -> float:
            ny = (y - ymin) / (ymax - ymin)
            return plot.bottom() - ny * plot.height()

        if ymin <= 0 <= ymax:
            p.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(plot.left(), my(0)), QPointF(plot.right(), my(0)))

        for i, r in enumerate(rows):
            cx = plot.left() + (i + 0.5) * slot
            bw = min(28.0, slot * 0.35)
            med = r.get("median_error_pct")
            q1 = r.get("q1_error_pct")
            q3 = r.get("q3_error_pct")
            mn = r.get("min_error_pct")
            mx = r.get("max_error_pct")
            p.setPen(QPen(accent, 1.5))
            if mn is not None and mx is not None:
                p.drawLine(QPointF(cx, my(float(mn))), QPointF(cx, my(float(mx))))
            if q1 is not None and q3 is not None:
                top, bot = my(float(q3)), my(float(q1))
                p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 40))
                p.drawRect(QRectF(cx - bw / 2, min(top, bot), bw, abs(bot - top)))
            if med is not None:
                p.setPen(QPen(ink, 2))
                yy = my(float(med))
                p.drawLine(QPointF(cx - bw / 2, yy), QPointF(cx + bw / 2, yy))
            for e in r.get("errors") or []:
                p.setBrush(accent)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, my(float(e))), 2.2, 2.2)
            p.setPen(muted)
            dpi = r.get("configured_dpi")
            label = str(int(dpi)) if dpi is not None and float(dpi).is_integer() else str(dpi)
            p.drawText(QRectF(cx - slot / 2, plot.bottom() + 4, slot, 16), Qt.AlignmentFlag.AlignHCenter, label)


class EngineeringDiagnosticsPanel(QWidget):
    """Advanced diagnostics — collapsed by default (Phase 3). Not Findings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._trials: list[Mapping[str, Any]] = []
        self._t: Callable[[str], str] | None = None
        self.toggle = QToolButton()
        self.toggle.setObjectName("TechToggle")
        self.toggle.setCheckable(True)
        self.toggle.setChecked(False)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle.toggled.connect(self._on_toggled)
        # Compat alias — older call sites / tests may read `.title`.
        self.title = self.toggle
        self.collapsed_hint = QLabel()
        self.collapsed_hint.setObjectName("PassiveHelper")
        self.collapsed_hint.setWordWrap(True)
        self.hint = QLabel()
        self.hint.setObjectName("Hint")
        self.hint.setWordWrap(True)
        self.filter_label = QLabel()
        self.dpi_filter = QComboBox()
        self.dpi_filter.currentIndexChanged.connect(self._rebuild)
        self.seq = _ScatterCanvas()
        self.dist = _ScatterCanvas()
        self.speed = _ScatterCanvas()
        self.latency = _ScatterCanvas()
        self.speed_note = QLabel()
        self.speed_note.setObjectName("Hint")
        self.speed_note.setWordWrap(True)
        self.latency_note = QLabel()
        self.latency_note.setObjectName("Hint")
        self.latency_note.setWordWrap(True)
        self.corr_note = QLabel()
        self.corr_note.setObjectName("Hint")
        self.corr_note.setWordWrap(True)
        self.n_note = QLabel()
        self.n_note.setObjectName("Hint")
        self.n_note.setWordWrap(True)
        filt = QHBoxLayout()
        filt.addWidget(self.filter_label)
        filt.addWidget(self.dpi_filter)
        filt.addStretch(1)
        self.body = QWidget()
        body_l = QVBoxLayout(self.body)
        body_l.setContentsMargins(0, 4, 0, 0)
        body_l.setSpacing(8)
        body_l.addWidget(self.hint)
        body_l.addLayout(filt)
        body_l.addWidget(self.n_note)
        body_l.addWidget(self.seq)
        body_l.addWidget(self.dist)
        body_l.addWidget(self.speed)
        body_l.addWidget(self.speed_note)
        body_l.addWidget(self.latency)
        body_l.addWidget(self.latency_note)
        body_l.addWidget(self.corr_note)
        self.body.setVisible(False)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        root.addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(self.collapsed_hint)
        root.addWidget(self.body)

    def _on_toggled(self, checked: bool) -> None:
        self.body.setVisible(checked)
        self.collapsed_hint.setVisible(not checked)
        self.toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def is_expanded(self) -> bool:
        return bool(self.toggle.isChecked())

    def set_expanded(self, expanded: bool) -> None:
        self.toggle.setChecked(bool(expanded))

    def set_localize(self, t: Callable[[str], str]) -> None:
        self._t = t
        self.toggle.setText(t("results.eng_diag_title"))
        self.collapsed_hint.setText(t("results.eng_diag_collapsed_hint"))
        self.hint.setText(t("results.eng_diag_hint"))
        self.filter_label.setText(t("results.dpi_filter"))

    def apply_tokens(self, tokens: ThemeTokens) -> None:
        self.seq.apply_tokens(tokens)
        self.dist.apply_tokens(tokens)
        self.speed.apply_tokens(tokens)
        self.latency.apply_tokens(tokens)

    def set_trials(self, trials: Sequence[Mapping[str, Any]]) -> None:
        self._trials = list(trials)
        dpis = sorted(
            {
                float(t["configured_dpi"])
                for t in trials
                if t.get("accepted")
                and not t.get("rejected")
                and not t.get("deleted")
                and t.get("configured_dpi") is not None
            }
        )
        t = self._t or (lambda k: k)
        cur = self.dpi_filter.currentData()
        self.dpi_filter.blockSignals(True)
        self.dpi_filter.clear()
        self.dpi_filter.addItem(t("results.dpi_filter_all"), None)
        for d in dpis:
            label = str(int(d)) if float(d).is_integer() else f"{d:g}"
            self.dpi_filter.addItem(label, d)
        if cur is not None:
            idx = self.dpi_filter.findData(cur)
            if idx >= 0:
                self.dpi_filter.setCurrentIndex(idx)
        self.dpi_filter.blockSignals(False)
        self._rebuild()

    def _rebuild(self) -> None:
        t = self._t or (lambda k: k)
        dpi = self.dpi_filter.currentData()
        seq = build_trial_sequence_points(self._trials, dpi_filter=dpi)
        self.seq.set_scatter(
            [(p.report_trial_no, p.error_pct, str(int(p.configured_dpi))) for p in seq],
            title=t("results.trial_sequence_title"),
            xlabel="Trial #",
            ylabel="CPI error %",
        )
        dist = build_dpi_error_distributions(self._trials)
        if dpi is not None:
            dist = [r for r in dist if abs(r.configured_dpi - float(dpi)) < 1e-9]
        n_bits = []
        for r in dist:
            iqr = None
            if r.q1_error_pct is not None and r.q3_error_pct is not None:
                iqr = r.q3_error_pct - r.q1_error_pct
            bit = f"{int(r.configured_dpi)} DPI: n={r.trial_count}"
            if r.median_error_pct is not None:
                bit += f", median={r.median_error_pct:+.2f}%"
            if iqr is not None:
                bit += f", IQR={iqr:.2f}"
            if r.trial_count < 8:
                bit += " (small n)"
            n_bits.append(bit)
        self.n_note.setText(" · ".join(n_bits) if n_bits else "")
        self.dist.set_box(
            [
                {
                    "configured_dpi": r.configured_dpi,
                    "median_error_pct": r.median_error_pct,
                    "q1_error_pct": r.q1_error_pct,
                    "q3_error_pct": r.q3_error_pct,
                    "min_error_pct": r.min_error_pct,
                    "max_error_pct": r.max_error_pct,
                    "errors": r.errors,
                    "trial_count": r.trial_count,
                }
                for r in dist
            ],
            title=t("results.trial_dist_title"),
            ylabel="CPI error %",
        )
        if not session_has_motion_timing(self._trials):
            self.speed.set_scatter([], title=t("results.speed_error_title"), xlabel="", ylabel="")
            self.latency.set_scatter(
                [], title=t("results.latency_error_title"), xlabel="", ylabel=""
            )
            self.speed_note.setText(t("results.speed_unavailable"))
            self.latency_note.setText("")
            self.corr_note.setText("")
            return
        pts = build_speed_error_points(self._trials)
        if dpi is not None:
            pts = [p for p in pts if abs(p.configured_dpi - float(dpi)) < 1e-9]
        self.speed.set_scatter(
            [
                (p.speed_mm_s, p.error_pct, str(int(p.configured_dpi)))
                for p in pts
            ],
            title=t("results.speed_error_title"),
            xlabel="Estimated traversal speed (mm/s)",
            ylabel="CPI error %",
        )
        self.speed_note.setText(t("results.speed_corr_wording"))
        lat = build_latency_error_points(self._trials)
        if dpi is not None:
            lat = [p for p in lat if abs(p.configured_dpi - float(dpi)) < 1e-9]
        self.latency.set_scatter(
            [
                (p.ready_to_first_motion_ms, p.error_pct, str(int(p.configured_dpi)))
                for p in lat
            ],
            title=t("results.latency_error_title"),
            xlabel="Ready-to-first-motion (ms)",
            ylabel="CPI error %",
        )
        self.latency_note.setText(t("results.latency_error_hint"))
        corr_bits = []
        for c in build_speed_correlations(self._trials):
            if dpi is not None and abs(c.configured_dpi - float(dpi)) > 1e-9:
                continue
            if c.spearman_rho is None:
                corr_bits.append(f"{int(c.configured_dpi)} DPI: n={c.n} (need ≥8 for Spearman)")
            else:
                corr_bits.append(
                    f"{int(c.configured_dpi)} DPI: n={c.n}, Spearman ρ={c.spearman_rho:+.3f}"
                )
        self.corr_note.setText(" · ".join(corr_bits))
