from datetime import datetime

import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.local_stats import DailyActivity, LocalStats


def _format_hour(hour: int) -> str:
    if hour == 0:
        return "12 AM"
    if hour < 12:
        return f"{hour} AM"
    if hour == 12:
        return "12 PM"
    return f"{hour - 12} PM"


def _short_model_name(model: str) -> str:
    if "opus-4-6" in model:
        return "Opus 4.6"
    if "opus-4-5" in model:
        return "Opus 4.5"
    if "sonnet" in model:
        return "Sonnet"
    if "haiku" in model:
        return "Haiku"
    return model.split("-")[0].title()


class ActivityChart(QWidget):
    """Bar chart showing daily activity over the last 30 days."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)

        header = QLabel("Daily Activity (last 30 days)")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        self._plot = pg.PlotWidget()
        self._plot.setBackground("w")
        self._plot.setFixedHeight(180)
        self._plot.showGrid(y=True, alpha=0.3)
        self._plot.getAxis("bottom").setStyle(showValues=False)
        layout.addWidget(self._plot)

        # Metric selector + total
        selector_row = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItems(["Messages", "Sessions", "Tool Calls"])
        self._combo.currentIndexChanged.connect(self._on_metric_changed)
        selector_row.addWidget(self._combo)

        self._total_label = QLabel("")
        self._total_label.setStyleSheet("font-size: 12px; color: #888;")
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        selector_row.addWidget(self._total_label, stretch=1)
        layout.addLayout(selector_row)

        self._data: list[DailyActivity] = []

    def set_data(self, daily_activity: list[DailyActivity]) -> None:
        # Keep last 30 days
        self._data = daily_activity[-30:]
        self._refresh_chart()

    def _on_metric_changed(self) -> None:
        self._refresh_chart()

    def _refresh_chart(self) -> None:
        self._plot.clear()
        if not self._data:
            return

        metric = self._combo.currentText()
        values = []
        for d in self._data:
            if metric == "Messages":
                values.append(d.message_count)
            elif metric == "Sessions":
                values.append(d.session_count)
            else:
                values.append(d.tool_call_count)

        x = list(range(len(values)))
        bar = pg.BarGraphItem(x=x, height=values, width=0.6, brush="#4CAF50")
        self._plot.addItem(bar)

        total = sum(values)
        self._total_label.setText(f"Total: {total:,}")


class InsightsPanel(QWidget):
    """Static insights computed from local stats."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)

        header = QLabel("Insights")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        self._content = QLabel("")
        self._content.setStyleSheet("font-size: 12px; color: #666; line-height: 1.6;")
        self._content.setWordWrap(True)
        layout.addWidget(self._content)

    def set_stats(self, stats: LocalStats) -> None:
        lines = []

        if stats.peak_hour is not None:
            lines.append(
                f"Peak hour: {_format_hour(stats.peak_hour)} ({stats.peak_hour_count} sessions)"
            )

        lines.append(f"Total sessions: {stats.total_sessions}")

        if stats.most_active_day:
            lines.append(
                f"Most active day: {stats.most_active_day} ({stats.most_active_day_messages:,} msgs)"
            )

        if stats.models_used:
            names = [_short_model_name(m) for m in stats.models_used]
            lines.append(f"Models: {', '.join(names)}")

        if stats.first_session_date:
            try:
                first = datetime.fromisoformat(stats.first_session_date)
                lines.append(f"Using since: {first.strftime('%b %-d, %Y')}")
            except ValueError:
                pass

        self._content.setText("\n".join(lines))
