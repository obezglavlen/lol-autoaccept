import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tkinterdnd2 import TkinterDnD
from PIL import Image

from main import LoLAutoAcceptApp
from process_selection import (
    ProcessTarget,
    load_process_selection,
    persist_process_selection,
)


class AppProcessSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = TkinterDnD.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.update_idletasks()
        self.root.update()
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_saved_process_is_restored_into_selector(self):
        base = Path(self.temp_dir.name)
        process_path = base / "app-data" / "selected_process.json"
        template_path = base / "app-data" / "accept_template.png"
        target = ProcessTarget(4321, "Example.exe", "Example window")
        persist_process_selection(target, process_path)

        app = LoLAutoAcceptApp(
            self.root,
            template_path=template_path,
            process_path=process_path,
            process_provider=lambda: [target],
        )

        self.assertEqual(app.selected_process, target)
        self.assertEqual(app.process_var.get(), target.label)
        self.assertIn(target.label, app.process_combo.cget("values"))

    def test_selecting_process_persists_it_for_next_launch(self):
        base = Path(self.temp_dir.name)
        process_path = base / "app-data" / "selected_process.json"
        template_path = base / "app-data" / "accept_template.png"
        first = ProcessTarget(111, "First.exe", "First window")
        second = ProcessTarget(222, "Second.exe", "Second window")
        app = LoLAutoAcceptApp(
            self.root,
            template_path=template_path,
            process_path=process_path,
            process_provider=lambda: [first, second],
        )

        app.process_combo.current(1)
        app._on_process_selected()

        self.assertEqual(app.selected_process, second)
        self.assertEqual(load_process_selection(process_path), second)

    def test_dropdown_choice_runs_process_selection_callback(self):
        base = Path(self.temp_dir.name)
        process_path = base / "app-data" / "selected_process.json"
        target = ProcessTarget(333, "Chosen.exe", "Chosen window")
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=process_path,
            process_provider=lambda: [target],
        )

        app.process_combo._choose(0)
        self.root.update_idletasks()
        self.root.update()

        self.assertEqual(load_process_selection(process_path), target)

    def test_default_provider_lists_processes_that_own_visible_windows(self):
        base = Path(self.temp_dir.name)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )
        window = SimpleNamespace(
            title="Editor window",
            visible=True,
            isMinimized=False,
            width=800,
            height=600,
        )
        process = SimpleNamespace(name=lambda: "Editor.exe")

        with (
            patch("main.pyautogui.getAllWindows", return_value=[window]),
            patch("main.psutil.Process", return_value=process),
            patch.object(app, "_window_process_id", return_value=9876, create=True),
        ):
            targets = app._list_window_processes()

        self.assertEqual(
            targets,
            [ProcessTarget(9876, "Editor.exe", "Editor window")],
        )

    def test_process_selector_uses_antialiased_rounded_surface(self):
        base = Path(self.temp_dir.name)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )

        self.assertEqual(
            len(app.process_combo.find_withtag("dropdown_surface")),
            1,
        )
        self.assertGreaterEqual(app.process_combo.radius, 10)

    def test_selected_window_lookup_ignores_other_processes(self):
        base = Path(self.temp_dir.name)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )
        other = SimpleNamespace(key="other", title="Other", visible=True, width=1600, height=900)
        small = SimpleNamespace(key="small", title="Small", visible=True, width=300, height=200)
        main = SimpleNamespace(key="main", title="Main", visible=True, width=900, height=700)
        pids = {"other": 11, "small": 22, "main": 22}
        app.selected_process = ProcessTarget(22, "Selected.exe", "Main")

        with (
            patch("main.pyautogui.getAllWindows", return_value=[other, small, main]),
            patch.object(app, "_window_process_id", side_effect=lambda window: pids[window.key]),
        ):
            selected_window = app._find_selected_window()

        self.assertIs(selected_window, main)

    def test_start_requires_a_selected_process(self):
        base = Path(self.temp_dir.name)
        image_path = base / "template.png"
        Image.new("RGB", (20, 10), "blue").save(image_path)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )
        app.image_path = str(image_path)

        with (
            patch("main.messagebox.showwarning") as showwarning,
            patch("main.messagebox.showerror"),
            patch.object(app, "_find_selected_window") as find_window,
        ):
            app.start_app()

        showwarning.assert_called_once()
        self.assertIn("process", showwarning.call_args.args[1].lower())
        find_window.assert_not_called()
        self.assertFalse(app.is_running)

    def test_start_scans_the_selected_process_window(self):
        base = Path(self.temp_dir.name)
        image_path = base / "template.png"
        Image.new("RGB", (20, 10), "blue").save(image_path)
        target = ProcessTarget(222, "Selected.exe", "Selected window")
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [target],
        )
        app.image_path = str(image_path)
        app.selected_process = target
        window = SimpleNamespace(
            left=100,
            top=200,
            width=800,
            height=600,
            visible=True,
            activate=MagicMock(),
        )

        with (
            patch.object(app, "_find_selected_window", return_value=window) as find_window,
            patch("main.threading.Thread") as thread_class,
        ):
            app.start_app()

        find_window.assert_called_once_with()
        self.assertIs(app.target_window, window)
        self.assertEqual(app._target_rect, (100, 200, 800, 600))
        thread_class.return_value.start.assert_called_once_with()
        self.assertTrue(app.is_running)

    def test_capture_is_cropped_to_selected_process_window(self):
        base = Path(self.temp_dir.name)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )
        app.target_window = SimpleNamespace(
            left=120,
            top=80,
            width=640,
            height=480,
        )
        screenshot_image = Image.new("RGB", (640, 480), "white")

        with patch("main.pyautogui.screenshot", return_value=screenshot_image) as screenshot:
            frame, rect = app._capture_target_frame()

        screenshot.assert_called_once_with(region=(120, 80, 640, 480))
        self.assertEqual(rect, (120, 80, 640, 480))
        self.assertEqual(frame.shape, (480, 640, 3))

    def test_monitor_clicks_match_inside_selected_process_window(self):
        base = Path(self.temp_dir.name)
        app = LoLAutoAcceptApp(
            self.root,
            template_path=base / "accept_template.png",
            process_path=base / "selected_process.json",
            process_provider=lambda: [],
        )
        app.selected_process = ProcessTarget(222, "Selected.exe", "Selected")
        app.target_window = SimpleNamespace(visible=True, isMinimized=False)
        app.is_running = True
        app._stop_event = MagicMock()
        app._stop_event.is_set.side_effect = [False, True]
        frame = Image.new("RGB", (640, 480), "white")

        with (
            patch.object(app, "_is_selected_process_running", return_value=True, create=True),
            patch.object(app, "_capture_target_frame", return_value=(frame, (120, 80, 640, 480))),
            patch.object(app, "search_accept_button", return_value=(30, 40)),
            patch("main.pyautogui.click") as click,
        ):
            app._run_monitor()

        click.assert_called_once_with(150, 120)
        self.assertEqual(app.status_label.cget("text"), "Target found — clicking")


if __name__ == "__main__":
    unittest.main()
