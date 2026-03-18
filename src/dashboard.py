from collections.abc import Callable
from datetime import datetime, timezone

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.api import UsageData, UsageWindow
from src.constants import (
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_TITLE,
)
from src.utils import color_for_utilization, format_reset_time_verbose


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

    def set_subtitle(self, text: str) -> None:
        """Set the subtitle text below the progress bar."""
        self._reset_label.setText(text)

    def update_data(self, window: UsageWindow) -> None:
        pct = min(int(window.utilization * 100), 100)
        self._bar.setValue(pct)

        display_pct = int(window.utilization * 100)
        if display_pct > 100:
            self._pct_label.setText("100+%")
        else:
            self._pct_label.setText(f"{display_pct}%")

        color = color_for_utilization(window.utilization)
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
        self._reset_label.setText(format_reset_time_verbose(window.resets_at))


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

        # Alerts settings
        alerts_header = QLabel("Alerts")
        alerts_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 12px;")
        self._layout.addWidget(alerts_header)

        threshold_row = QHBoxLayout()
        threshold_row.setContentsMargins(0, 0, 0, 0)
        self._threshold_check = QCheckBox("5h usage alert at:")
        self._threshold_check.setStyleSheet("font-size: 12px;")
        threshold_row.addWidget(self._threshold_check)
        threshold_row.addSpacing(4)

        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(10, 100)
        self._threshold_spin.setValue(70)
        self._threshold_spin.setFixedWidth(60)
        threshold_row.addWidget(self._threshold_spin)

        pct_label = QLabel("%")
        pct_label.setStyleSheet("font-size: 12px;")
        threshold_row.addWidget(pct_label)

        threshold_row.addStretch()
        self._layout.addLayout(threshold_row)

        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 4, 0, 8)
        self._reset_check = QCheckBox("Notify when usage window resets")
        self._reset_check.setStyleSheet("font-size: 12px;")
        reset_row.addWidget(self._reset_check)
        reset_row.addStretch()
        self._layout.addLayout(reset_row)

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

    def get_layout(self) -> QVBoxLayout:
        """Return the main content layout for widget replacement."""
        return self._layout

    def set_refresh_callback(self, callback: Callable[[], None]) -> None:
        self._refresh_btn.clicked.connect(callback)

    def set_refresh_enabled(self, enabled: bool) -> None:
        self._refresh_btn.setEnabled(enabled)

    def set_threshold_callback(self, callback: Callable[[], None]) -> None:
        self._threshold_spin.valueChanged.connect(callback)

    def set_threshold_enabled_callback(self, callback: Callable[[], None]) -> None:
        self._threshold_check.stateChanged.connect(callback)

    def set_reset_alerts_callback(self, callback: Callable[[], None]) -> None:
        self._reset_check.stateChanged.connect(callback)

    def set_threshold_spin_enabled(self, enabled: bool) -> None:
        self._threshold_spin.setEnabled(enabled)

    def update_alert_settings(
        self, threshold: float, threshold_enabled: bool, reset_enabled: bool
    ) -> None:
        self._threshold_spin.blockSignals(True)
        self._threshold_spin.setValue(int(threshold * 100))
        self._threshold_spin.blockSignals(False)

        self._threshold_check.blockSignals(True)
        self._threshold_check.setChecked(threshold_enabled)
        self._threshold_spin.setEnabled(threshold_enabled)
        self._threshold_check.blockSignals(False)

        self._reset_check.blockSignals(True)
        self._reset_check.setChecked(reset_enabled)
        self._reset_check.blockSignals(False)

    def update_usage(self, data: UsageData) -> None:
        self._five_hour_bar.update_data(data.five_hour)
        self._seven_day_bar.update_data(data.seven_day)

        if data.seven_day_opus:
            self._opus_bar.update_data(data.seven_day_opus)
            self._opus_bar.setVisible(True)
        else:
            self._opus_bar.setVisible(False)

        if data.extra_usage and data.extra_usage.is_enabled:
            extra_window = UsageWindow(
                utilization=data.extra_usage.utilization,
                resets_at=None,
            )
            self._extra_bar.update_data(extra_window)
            self._extra_bar.set_subtitle(
                f"${data.extra_usage.used_credits:.2f} / ${data.extra_usage.monthly_limit:.2f} monthly"
            )
            self._extra_bar.setVisible(True)
        else:
            self._extra_bar.setVisible(False)

        self.update_status_time(data.fetched_at)

    def update_status_time(self, fetched_at: datetime) -> None:
        """Lightweight update of just the 'last updated' label."""
        elapsed = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        if elapsed < 60:
            self._status_label.setText(f"Last updated: {int(elapsed)} seconds ago")
        else:
            self._status_label.setText(f"Last updated: {int(elapsed // 60)} minutes ago")

    def update_error(self, error: str) -> None:
        self._status_label.setText(f"Error: {error}")
        self._status_label.setWordWrap(True)

    def get_chart_placeholder(self) -> QWidget:
        return self._chart_placeholder

    def get_insights_placeholder(self) -> QWidget:
        return self._insights_placeholder

    def closeEvent(self, event) -> None:
        """Hide instead of close — the tray keeps running."""
        event.ignore()
        self.hide()
