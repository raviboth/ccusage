from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.api import UsageData, UsageWindow
from src.constants import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    THRESHOLD_RED,
    THRESHOLD_YELLOW,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_TITLE,
)


def _color_for_util(util: float) -> str:
    if util >= THRESHOLD_RED:
        return COLOR_RED
    if util >= THRESHOLD_YELLOW:
        return COLOR_YELLOW
    return COLOR_GREEN


def _format_reset(resets_at: datetime | None) -> str:
    if resets_at is None:
        return "No reset scheduled"
    now = datetime.now(timezone.utc)
    delta = resets_at - now
    if delta.total_seconds() <= 0:
        return "Resetting now"

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 and days == 0:
        parts.append(f"{minutes}m")
    relative = " ".join(parts) if parts else "soon"

    local_reset = resets_at.astimezone()
    if days == 0:
        absolute = local_reset.strftime("%-I:%M %p today")
    elif days < 7:
        absolute = local_reset.strftime("%a at %-I:%M %p")
    else:
        absolute = local_reset.strftime("%b %-d at %-I:%M %p")

    return f"Resets in {relative} \u00b7 {absolute}"


class UsageBar(QWidget):
    """A labeled progress bar for a usage window."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title_label)

        bar_row = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(20)
        bar_row.addWidget(self._bar, stretch=1)

        self._pct_label = QLabel("—")
        self._pct_label.setStyleSheet("font-size: 14px; font-weight: bold; min-width: 45px;")
        self._pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar_row.addWidget(self._pct_label)
        layout.addLayout(bar_row)

        self._reset_label = QLabel("")
        self._reset_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(self._reset_label)

    def update_data(self, window: UsageWindow) -> None:
        pct = min(int(window.utilization * 100), 100)
        self._bar.setValue(pct)

        display_pct = int(window.utilization * 100)
        if display_pct > 100:
            self._pct_label.setText("100+%")
        else:
            self._pct_label.setText(f"{display_pct}%")

        color = _color_for_util(window.utilization)
        self._bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
            """
        )
        self._pct_label.setStyleSheet(
            f"font-size: 14px; font-weight: bold; min-width: 45px; color: {color};"
        )
        self._reset_label.setText(_format_reset(window.resets_at))


class DashboardWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        # Main scrollable layout
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(20, 16, 20, 16)
        self._layout.setSpacing(0)

        # Usage bars
        self._five_hour_bar = UsageBar("5-Hour Limit")
        self._layout.addWidget(self._five_hour_bar)

        self._seven_day_bar = UsageBar("7-Day Limit")
        self._layout.addWidget(self._seven_day_bar)

        self._opus_bar = UsageBar("7-Day Opus")
        self._layout.addWidget(self._opus_bar)
        self._opus_bar.setVisible(False)

        self._extra_bar = UsageBar("Extra Usage")
        self._layout.addWidget(self._extra_bar)
        self._extra_bar.setVisible(False)

        # Last updated + refresh
        status_row = QHBoxLayout()
        self._status_label = QLabel("Waiting for data...")
        self._status_label.setStyleSheet("font-size: 11px; color: #aaa;")
        status_row.addWidget(self._status_label, stretch=1)

        self._refresh_btn = QPushButton("\u21bb")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.setToolTip("Refresh Now")
        status_row.addWidget(self._refresh_btn)
        self._layout.addLayout(status_row)

        # Placeholder for charts (added later)
        self._chart_placeholder = QWidget()
        self._layout.addWidget(self._chart_placeholder)

        # Placeholder for insights (added later)
        self._insights_placeholder = QWidget()
        self._layout.addWidget(self._insights_placeholder)

        self._layout.addStretch()

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_refresh_callback(self, callback: callable) -> None:
        self._refresh_btn.clicked.connect(callback)

    def update_usage(self, data: UsageData) -> None:
        self._five_hour_bar.update_data(data.five_hour)
        self._seven_day_bar.update_data(data.seven_day)

        if data.seven_day_opus:
            self._opus_bar.update_data(data.seven_day_opus)
            self._opus_bar.setVisible(True)
        else:
            self._opus_bar.setVisible(False)

        if data.extra_usage and data.extra_usage.is_enabled:
            from src.api import UsageWindow
            extra_window = UsageWindow(
                utilization=data.extra_usage.utilization,
                resets_at=None,
            )
            self._extra_bar.update_data(extra_window)
            self._extra_bar._reset_label.setText(
                f"${data.extra_usage.used_credits:.2f} / ${data.extra_usage.monthly_limit:.2f} monthly"
            )
            self._extra_bar.setVisible(True)
        else:
            self._extra_bar.setVisible(False)

        elapsed = (datetime.now(timezone.utc) - data.fetched_at).total_seconds()
        if elapsed < 60:
            self._status_label.setText(f"Last updated: {int(elapsed)} seconds ago")
        else:
            self._status_label.setText(f"Last updated: {int(elapsed // 60)} minutes ago")

    def update_error(self, error: str) -> None:
        self._status_label.setText(f"Error: {error}")

    def get_chart_placeholder(self) -> QWidget:
        return self._chart_placeholder

    def get_insights_placeholder(self) -> QWidget:
        return self._insights_placeholder

    def closeEvent(self, event) -> None:
        """Hide instead of close — the tray keeps running."""
        event.ignore()
        self.hide()
