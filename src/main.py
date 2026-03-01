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
from src.tray import TrayManager


class Signals(QObject):
    """Bridge between the polling thread and the Qt main thread."""

    usage_updated = pyqtSignal(object)  # UsageData or None
    usage_error = pyqtSignal(str)


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
        self._running = True

        # Dashboard
        self._dashboard = DashboardWindow()
        self._dashboard.set_refresh_callback(self._on_refresh)

        # Charts + insights
        self._chart = ActivityChart()
        self._insights = InsightsPanel()

        # Replace placeholders in dashboard layout
        dash_layout = self._dashboard._layout
        dash_layout.replaceWidget(self._dashboard.get_chart_placeholder(), self._chart)
        self._dashboard.get_chart_placeholder().deleteLater()

        dash_layout.replaceWidget(self._dashboard.get_insights_placeholder(), self._insights)
        self._dashboard.get_insights_placeholder().deleteLater()

        # Load local stats
        stats = load_local_stats()
        if stats:
            self._chart.set_data(stats.daily_activity)
            self._insights.set_stats(stats)

        # Tray (QSystemTrayIcon — runs in Qt event loop, no separate thread)
        self._tray = TrayManager(
            on_open_dashboard=self._on_open_dashboard,
            on_refresh=self._on_refresh,
            on_quit=self._on_quit,
        )

        # Signal connections
        self._signals.usage_updated.connect(self._handle_usage_update)
        self._signals.usage_error.connect(self._handle_usage_error)

        # Status label timer — update "X seconds ago" every 10s
        self._last_data: UsageData | None = None
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._refresh_status_time)
        self._status_timer.start(10_000)

    def _poll_once(self) -> None:
        auth = get_oauth_token()
        if auth.error or not auth.access_token:
            self._signals.usage_error.emit(auth.error or "No token available.")
            return

        token = auth.access_token
        del auth
        result: UsageResult = fetch_usage(token)
        del token
        if result.error or not result.data:
            self._signals.usage_error.emit(result.error or "Unknown error.")
            return

        self._db.insert_snapshot(result.data)
        self._signals.usage_updated.emit(result.data)

    def _poll_loop(self) -> None:
        while self._running:
            self._poll_once()
            for _ in range(POLL_INTERVAL_SECONDS * 10):
                if not self._running:
                    return
                time.sleep(0.1)

    def _handle_usage_update(self, data: UsageData) -> None:
        self._last_data = data
        self._tray.update(data, None)
        self._dashboard.update_usage(data)

    def _handle_usage_error(self, error: str) -> None:
        self._tray.update(None, error)
        self._dashboard.update_error(error)

    def _refresh_status_time(self) -> None:
        if self._last_data:
            self._dashboard.update_usage(self._last_data)

    def _on_open_dashboard(self, *_args) -> None:
        self._dashboard.show()
        self._dashboard.raise_()
        self._dashboard.activateWindow()

    def _on_refresh(self, *_args) -> None:
        threading.Thread(target=self._poll_once, daemon=True).start()

    def _on_quit(self, *_args) -> None:
        self._running = False
        self._tray.hide()
        self._db.prune_old()
        self._db.close()
        self._qt_app.quit()

    def run(self) -> None:
        # Show tray icon
        self._tray.show()

        # Start polling in background thread
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()

        # Run Qt event loop on main thread (blocks until quit)
        sys.exit(self._qt_app.exec())


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
