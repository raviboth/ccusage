import json
import os
import tempfile
from datetime import datetime

from plyer import notification

from src.api import UsageData
from src.constants import APP_DATA_DIR

SETTINGS_FILE = APP_DATA_DIR / "settings.json"

DEFAULT_THRESHOLD = 0.70
DEFAULT_THRESHOLD_ENABLED = True
DEFAULT_RESET_NOTIFICATIONS = False


class NotificationManager:
    def __init__(self) -> None:
        # 5h settings
        self._threshold: float = DEFAULT_THRESHOLD
        self._threshold_enabled: bool = DEFAULT_THRESHOLD_ENABLED
        self._reset_notifications: bool = DEFAULT_RESET_NOTIFICATIONS
        self._threshold_fired: bool = False
        self._last_resets_at: datetime | None = None

        # 7d settings
        self._seven_day_threshold: float = DEFAULT_THRESHOLD
        self._seven_day_threshold_enabled: bool = DEFAULT_THRESHOLD_ENABLED
        self._seven_day_reset_notifications: bool = DEFAULT_RESET_NOTIFICATIONS
        self._seven_day_threshold_fired: bool = False
        self._seven_day_last_resets_at: datetime | None = None

        self._load_settings()

    def _load_settings(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                self._threshold = float(data.get("threshold", DEFAULT_THRESHOLD))
                self._threshold_enabled = bool(
                    data.get("threshold_enabled", DEFAULT_THRESHOLD_ENABLED)
                )
                self._reset_notifications = bool(
                    data.get("reset_notifications", DEFAULT_RESET_NOTIFICATIONS)
                )
                self._seven_day_threshold = float(
                    data.get("seven_day_threshold", DEFAULT_THRESHOLD)
                )
                self._seven_day_threshold_enabled = bool(
                    data.get("seven_day_threshold_enabled", DEFAULT_THRESHOLD_ENABLED)
                )
                self._seven_day_reset_notifications = bool(
                    data.get("seven_day_reset_notifications", DEFAULT_RESET_NOTIFICATIONS)
                )
            except (json.JSONDecodeError, ValueError, OSError):
                pass

    def _save_settings(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(APP_DATA_DIR), suffix=".tmp", prefix="settings_"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(
                    {
                        "threshold": self._threshold,
                        "threshold_enabled": self._threshold_enabled,
                        "reset_notifications": self._reset_notifications,
                        "seven_day_threshold": self._seven_day_threshold,
                        "seven_day_threshold_enabled": self._seven_day_threshold_enabled,
                        "seven_day_reset_notifications": self._seven_day_reset_notifications,
                    },
                    f,
                    indent=2,
                )
            os.replace(tmp_path, str(SETTINGS_FILE))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # -- 5h properties --

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def threshold_enabled(self) -> bool:
        return self._threshold_enabled

    @property
    def reset_notifications(self) -> bool:
        return self._reset_notifications

    # -- 7d properties --

    @property
    def seven_day_threshold(self) -> float:
        return self._seven_day_threshold

    @property
    def seven_day_threshold_enabled(self) -> bool:
        return self._seven_day_threshold_enabled

    @property
    def seven_day_reset_notifications(self) -> bool:
        return self._seven_day_reset_notifications

    # -- check --

    def check(self, data: UsageData) -> None:
        self._check_five_hour(data)
        self._check_seven_day(data)

    def _check_five_hour(self, data: UsageData) -> None:
        util = data.five_hour.utilization

        if not self._threshold_enabled:
            self._threshold_fired = False
        elif util >= self._threshold:
            if not self._threshold_fired:
                self._threshold_fired = True
                pct = int(self._threshold * 100)
                cur = int(util * 100)
                self._notify(
                    title="Claude Code Usage Alert",
                    message=f"5h utilization reached {cur}% (threshold: {pct}%)",
                )
        else:
            self._threshold_fired = False

        if self._reset_notifications:
            current_resets_at = data.five_hour.resets_at
            if (
                self._last_resets_at is not None
                and current_resets_at != self._last_resets_at
                and util < self._threshold
            ):
                self._notify(
                    title="Claude Code Usage Reset",
                    message="5h usage window has reset.",
                )
            self._last_resets_at = current_resets_at

    def _check_seven_day(self, data: UsageData) -> None:
        util = data.seven_day.utilization

        if not self._seven_day_threshold_enabled:
            self._seven_day_threshold_fired = False
        elif util >= self._seven_day_threshold:
            if not self._seven_day_threshold_fired:
                self._seven_day_threshold_fired = True
                pct = int(self._seven_day_threshold * 100)
                cur = int(util * 100)
                self._notify(
                    title="Claude Code Usage Alert",
                    message=f"7d utilization reached {cur}% (threshold: {pct}%)",
                )
        else:
            self._seven_day_threshold_fired = False

        if self._seven_day_reset_notifications:
            current_resets_at = data.seven_day.resets_at
            if (
                self._seven_day_last_resets_at is not None
                and current_resets_at != self._seven_day_last_resets_at
                and util < self._seven_day_threshold
            ):
                self._notify(
                    title="Claude Code Usage Reset",
                    message="7d usage window has reset.",
                )
            self._seven_day_last_resets_at = current_resets_at

    # -- 5h setters --

    def update_threshold(self, value: float) -> None:
        self._threshold = value
        self._threshold_fired = False
        self._save_settings()

    def set_threshold_enabled(self, enabled: bool) -> None:
        self._threshold_enabled = enabled
        self._threshold_fired = False
        self._save_settings()

    def set_reset_notifications(self, enabled: bool) -> None:
        self._reset_notifications = enabled
        self._save_settings()

    # -- 7d setters --

    def update_seven_day_threshold(self, value: float) -> None:
        self._seven_day_threshold = value
        self._seven_day_threshold_fired = False
        self._save_settings()

    def set_seven_day_threshold_enabled(self, enabled: bool) -> None:
        self._seven_day_threshold_enabled = enabled
        self._seven_day_threshold_fired = False
        self._save_settings()

    def set_seven_day_reset_notifications(self, enabled: bool) -> None:
        self._seven_day_reset_notifications = enabled
        self._save_settings()

    @staticmethod
    def _notify(title: str, message: str) -> None:
        try:
            notification.notify(title=title, message=message, timeout=10)
        except Exception:
            pass
