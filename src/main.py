import sys
import threading
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.api import UsageData, UsageResult, fetch_usage
from src.auth import get_oauth_token
from src.charts import ActivityChart, InsightsPanel
from src.constants import POLL_INTERVAL_SECONDS
from src.dashboard import DashboardWindow
from src.db import UsageDB
from src.local_stats import load_local_stats
from src.notifications import NotificationManager
from src.tray import TrayManager


class Signals(QObject):
    """Bridge between the polling thread and the Qt main thread."""

    usage_updated = pyqtSignal(object)  # UsageData or None
    usage_error = pyqtSignal(str)
    refresh_done = pyqtSignal()


class App:
    def __init__(self) -> None:
        self._qt_app = QApplication(sys.argv)
        # Keep app running even when all windows are closed (tray stays)
        self._qt_app.setQuitOnLastWindowClosed(False)

        # On macOS, allow the app to show windows from background
        if sys.platform == "darwin":
            import AppKit
            AppKit.NSApplication.sharedApplication().setActivationPolicy_(0)  # Regular

        self._signals = Signals()
        self._db = UsageDB()
        self._db.prune_old()
        self._running = True

        # Notifications
        self._notifications = NotificationManager()

        # Dashboard
        self._dashboard = DashboardWindow()
        self._dashboard.set_refresh_callback(self._on_refresh)
        self._dashboard.set_threshold_callback(self._on_threshold_changed)
        self._dashboard.set_threshold_enabled_callback(self._on_threshold_enabled_changed)
        self._dashboard.set_reset_alerts_callback(self._on_reset_alerts_changed)
        self._dashboard.update_alert_settings(
            self._notifications.threshold,
            self._notifications.threshold_enabled,
            self._notifications.reset_notifications,
        )

        # Charts + insights
        self._chart = ActivityChart()
        self._insights = InsightsPanel()

        # Replace placeholders in dashboard layout
        dash_layout = self._dashboard.get_layout()
        dash_layout.replaceWidget(self._dashboard.get_chart_placeholder(), self._chart)
        self._dashboard.get_chart_placeholder().deleteLater()

        dash_layout.replaceWidget(self._dashboard.get_insights_placeholder(), self._insights)
        self._dashboard.get_insights_placeholder().deleteLater()

        # Load local stats
        stats = load_local_stats()
        if stats:
            self._chart.set_data(stats.daily_activity)
            self._insights.set_stats(stats)

        # Tray (QSystemTrayIcon -- runs in Qt event loop, no separate thread)
        self._tray = TrayManager(
            on_open_dashboard=self._on_open_dashboard,
            on_refresh=self._on_refresh,
            on_quit=self._on_quit,
        )

        # Signal connections
        self._signals.usage_updated.connect(self._handle_usage_update)
        self._signals.usage_error.connect(self._handle_usage_error)
        self._signals.refresh_done.connect(self._on_refresh_done)

        # Status label timer -- update "X seconds ago" every 10s
        self._last_data: UsageData | None = None
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._refresh_status_time)
        self._status_timer.start(10_000)

    def _poll_once(self) -> UsageResult | None:
        auth = get_oauth_token()
        if auth.error or not auth.access_token:
            self._signals.usage_error.emit(auth.error or "No token available.")
            return None

        token = auth.access_token
        del auth
        result: UsageResult = fetch_usage(token)
        del token
        if result.error or not result.data:
            self._signals.usage_error.emit(result.error or "Unknown error.")
            return result

        self._db.insert_snapshot(result.data)
        self._signals.usage_updated.emit(result.data)
        return result

    def _poll_loop(self) -> None:
        consecutive_errors = 0
        while self._running:
            result = self._poll_once()
            if result and result.data:
                consecutive_errors = 0
                wait = POLL_INTERVAL_SECONDS
            else:
                consecutive_errors = min(consecutive_errors + 1, 5)
                # Respect Retry-After header from 429 responses
                if result and result.retry_after:
                    wait = max(result.retry_after, POLL_INTERVAL_SECONDS)
                else:
                    wait = min(POLL_INTERVAL_SECONDS * (2 ** consecutive_errors), 600)
            for _ in range(int(wait * 10)):
                if not self._running:
                    return
                time.sleep(0.1)

    def _handle_usage_update(self, data: UsageData) -> None:
        self._last_data = data
        self._tray.update(data, None)
        self._dashboard.update_usage(data)
        self._notifications.check(data)

    def _handle_usage_error(self, error: str) -> None:
        self._tray.update(None, error)
        self._dashboard.update_error(error)

    def _refresh_status_time(self) -> None:
        if self._last_data:
            self._dashboard.update_status_time(self._last_data.fetched_at)

    def _on_open_dashboard(self, *_args) -> None:
        stats = load_local_stats()
        if stats:
            self._chart.set_data(stats.daily_activity)
            self._insights.set_stats(stats)
        self._dashboard.show()
        self._dashboard.raise_()
        self._dashboard.activateWindow()

    def _on_refresh(self, *_args) -> None:
        self._dashboard.set_refresh_enabled(False)

        def _do_refresh() -> None:
            self._poll_once()
            self._signals.refresh_done.emit()

        threading.Thread(target=_do_refresh, daemon=True).start()

    def _on_refresh_done(self) -> None:
        self._dashboard.set_refresh_enabled(True)

    def _on_quit(self, *_args) -> None:
        self._running = False
        self._tray.hide()
        if hasattr(self, '_poll_thread'):
            self._poll_thread.join(timeout=2.0)
        self._db.prune_old()
        self._db.close()
        self._qt_app.quit()

    def _on_threshold_changed(self, value: int) -> None:
        self._notifications.update_threshold(value / 100.0)

    def _on_threshold_enabled_changed(self, state: int) -> None:
        enabled = state != 0
        self._notifications.set_threshold_enabled(enabled)
        self._dashboard.set_threshold_spin_enabled(enabled)

    def _on_reset_alerts_changed(self, state: int) -> None:
        self._notifications.set_reset_notifications(state != 0)

    def run(self) -> None:
        # Show tray icon
        self._tray.show()

        # Start polling in background thread
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        # Run Qt event loop on main thread (blocks until quit)
        sys.exit(self._qt_app.exec())


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
