import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional


user32 = ctypes.windll.user32


@dataclass
class WindowRegion:
    hwnd: int
    left: int
    top: int
    width: int
    height: int


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def get_window_title(hwnd: int) -> str:
    return _get_window_text(hwnd)


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def find_window_by_title_substring(substring: str) -> Optional[int]:
    target = substring.lower()
    result = {"hwnd": None}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_handler(hwnd, _lparam):
        if not _is_window_visible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if title and target in title.lower():
            result["hwnd"] = int(hwnd)
            return False
        return True

    user32.EnumWindows(enum_handler, 0)
    return result["hwnd"]


def get_client_region(hwnd: int) -> Optional[WindowRegion]:
    client = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(client)):
        return None

    origin = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        return None

    width = int(client.right - client.left)
    height = int(client.bottom - client.top)
    if width <= 0 or height <= 0:
        return None

    return WindowRegion(
        hwnd=hwnd,
        left=int(origin.x),
        top=int(origin.y),
        width=width,
        height=height,
    )
