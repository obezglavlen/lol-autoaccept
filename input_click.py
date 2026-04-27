import ctypes
import time
from dataclasses import dataclass


user32 = ctypes.windll.user32

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


@dataclass
class ClickGuard:
    cooldown_sec: float
    _last_click_ts: float = 0.0

    def can_click(self) -> bool:
        return (time.time() - self._last_click_ts) >= self.cooldown_sec

    def mark_clicked(self) -> None:
        self._last_click_ts = time.time()


def _to_absolute(x: int, y: int) -> tuple[int, int]:
    screen_w = user32.GetSystemMetrics(0)
    screen_h = user32.GetSystemMetrics(1)
    abs_x = int(x * 65535 / max(screen_w - 1, 1))
    abs_y = int(y * 65535 / max(screen_h - 1, 1))
    return abs_x, abs_y


def click_screen_point(x: int, y: int) -> None:
    abs_x, abs_y = _to_absolute(x, y)
    user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
