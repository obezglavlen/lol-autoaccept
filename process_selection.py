"""Persisted process selection and window-target helpers."""

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from uuid import uuid4

from image_storage import APP_DIRECTORY_NAME


PROCESS_FILENAME = "selected_process.json"


@dataclass(frozen=True)
class ProcessTarget:
    """A running process that owns at least one visible window."""

    pid: int
    name: str
    window_title: str = ""

    @property
    def label(self):
        title = self.window_title.strip()
        suffix = f" — {title}" if title else ""
        return f"{self.name}{suffix}  (PID {self.pid})"


def collect_window_processes(
    windows,
    *,
    pid_resolver,
    name_resolver,
    excluded_pids=(),
):
    """Return one target per process, represented by its largest window."""
    excluded = {int(pid) for pid in excluded_pids}
    largest_by_pid = {}

    for window in windows:
        title = str(getattr(window, "title", "")).strip()
        width = int(getattr(window, "width", 0) or 0)
        height = int(getattr(window, "height", 0) or 0)
        if (
            not title
            or not getattr(window, "visible", True)
            or getattr(window, "isMinimized", False)
            or width <= 0
            or height <= 0
        ):
            continue

        try:
            pid = int(pid_resolver(window))
            if pid <= 0 or pid in excluded:
                continue
            name = str(name_resolver(pid)).strip()
        except Exception:
            continue
        if not name:
            continue

        area = width * height
        current = largest_by_pid.get(pid)
        if current is None or area > current[0]:
            largest_by_pid[pid] = (
                area,
                ProcessTarget(pid=pid, name=name, window_title=title),
            )

    return sorted(
        (entry[1] for entry in largest_by_pid.values()),
        key=lambda target: (
            target.name.casefold(),
            target.window_title.casefold(),
            target.pid,
        ),
    )


def default_process_path():
    """Return the durable per-user path for the selected process."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_directory = (
        Path(local_app_data)
        if local_app_data
        else Path.home() / ".local" / "share"
    )
    return base_directory / APP_DIRECTORY_NAME / PROCESS_FILENAME


def persist_process_selection(target, destination_path):
    """Atomically save a process target as UTF-8 JSON."""
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")

    try:
        temporary.write_text(
            json.dumps(asdict(target), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    return destination


def load_process_selection(source_path):
    """Load a valid saved process target, or return None."""
    try:
        payload = json.loads(Path(source_path).read_text(encoding="utf-8"))
        pid = int(payload["pid"])
        name = str(payload["name"]).strip()
        window_title = str(payload.get("window_title", "")).strip()
        if pid <= 0 or not name:
            return None
        return ProcessTarget(pid=pid, name=name, window_title=window_title)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
