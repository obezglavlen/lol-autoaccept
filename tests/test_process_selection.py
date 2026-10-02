import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from process_selection import (
    ProcessTarget,
    collect_window_processes,
    default_process_path,
    load_process_selection,
    persist_process_selection,
)


class ProcessSelectionStorageTests(unittest.TestCase):
    def test_default_process_path_uses_same_local_app_data_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                path = default_process_path()

        self.assertEqual(
            path,
            Path(temp_dir) / "LoLAutoAccept" / "selected_process.json",
        )

    def test_process_selection_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "app-data" / "selected_process.json"
            target = ProcessTarget(
                pid=4321,
                name="Example App.exe",
                window_title="Example document",
            )

            persist_process_selection(target, destination)
            restored = load_process_selection(destination)

        self.assertEqual(restored, target)

    def test_invalid_saved_process_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "selected_process.json"
            destination.write_text("not-json", encoding="utf-8")

            restored = load_process_selection(destination)

        self.assertIsNone(restored)


class WindowProcessCollectionTests(unittest.TestCase):
    def test_collects_one_largest_visible_window_per_process(self):
        windows = [
            SimpleNamespace(key="small", title="Small", visible=True, width=200, height=100),
            SimpleNamespace(key="large", title="Main window", visible=True, width=900, height=700),
            SimpleNamespace(key="other", title="Other", visible=True, width=500, height=400),
            SimpleNamespace(key="hidden", title="Hidden", visible=False, width=1000, height=800),
        ]
        pids = {"small": 10, "large": 10, "other": 20, "hidden": 30}
        names = {10: "Editor.exe", 20: "Browser.exe", 30: "Hidden.exe"}

        targets = collect_window_processes(
            windows,
            pid_resolver=lambda window: pids[window.key],
            name_resolver=lambda pid: names[pid],
        )

        self.assertEqual(
            targets,
            [
                ProcessTarget(20, "Browser.exe", "Other"),
                ProcessTarget(10, "Editor.exe", "Main window"),
            ],
        )

    def test_inaccessible_process_does_not_hide_other_windows(self):
        windows = [
            SimpleNamespace(key="denied", title="Denied", visible=True, width=300, height=200),
            SimpleNamespace(key="good", title="Available", visible=True, width=400, height=300),
        ]
        pids = {"denied": 10, "good": 20}

        def process_name(pid):
            if pid == 10:
                raise RuntimeError("access denied")
            return "Available.exe"

        targets = collect_window_processes(
            windows,
            pid_resolver=lambda window: pids[window.key],
            name_resolver=process_name,
        )

        self.assertEqual(
            targets,
            [ProcessTarget(20, "Available.exe", "Available")],
        )


if __name__ == "__main__":
    unittest.main()
