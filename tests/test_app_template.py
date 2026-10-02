import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from tkinterdnd2 import TkinterDnD

from image_storage import persist_template
from main import LoLAutoAcceptApp, ModernStyle


class AppTemplateRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = TkinterDnD.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.update_idletasks()
        self.root.update()
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_saved_template_is_restored_during_startup(self):
        temp_path = Path(self.temp_dir.name)
        source = temp_path / "source.png"
        saved_template = temp_path / "app-data" / "accept_template.png"
        Image.new("RGB", (20, 10), (20, 120, 220)).save(source)
        persist_template(source, saved_template)

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)
        self.root.update_idletasks()

        self.assertEqual(Path(app.image_path), saved_template)
        self.assertEqual(len(app.image_canvas.find_withtag("template_preview")), 1)

    def test_dropped_image_is_loaded_and_saved(self):
        temp_path = Path(self.temp_dir.name)
        source = temp_path / "source image.png"
        saved_template = temp_path / "app-data" / "accept_template.png"
        Image.new("RGB", (20, 10), (220, 120, 20)).save(source)
        app = LoLAutoAcceptApp(self.root, template_path=saved_template)
        event = SimpleNamespace(data=f"{{{source.as_posix()}}}", action="copy")

        result = app._on_image_drop(event)

        self.assertEqual(result, "copy")
        self.assertEqual(Path(app.image_path), saved_template)
        self.assertTrue(saved_template.is_file())

    def test_image_canvas_has_a_native_drop_binding(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        self.assertTrue(app.image_canvas.dnd_bind("<<Drop>>"))

    def test_empty_canvas_is_presented_as_a_drop_zone(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        placeholder_text = app.image_canvas.itemcget(app.image_placeholder, "text")
        self.assertIn("Drop image here", placeholder_text)
        self.assertEqual(len(app.image_canvas.find_withtag("drop_border")), 1)

    def test_interface_uses_apple_light_palette(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        self.assertEqual(ModernStyle.COLORS["primary"], "#0071e3")
        self.assertEqual(ModernStyle.COLORS["bg_app"], "#f5f5f7")
        self.assertEqual(ModernStyle.COLORS["bg_card"], "#ffffff")
        self.assertEqual(app.root.cget("bg"), "#f5f5f7")

    def test_interface_has_premium_title_and_pill_primary_action(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        self.assertEqual(app.title_label.cget("text"), "Auto Accept")
        self.assertGreaterEqual(app.start_btn.radius, 20)
        self.assertEqual(app.start_btn.current_fill, ModernStyle.COLORS["primary"])

    def test_window_has_a_branded_icon(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        self.assertEqual(app.app_icon.width(), 32)
        self.assertEqual(app.app_icon.height(), 32)

    def test_primary_button_uses_antialiased_image_surface(self):
        saved_template = Path(self.temp_dir.name) / "app-data" / "accept_template.png"

        app = LoLAutoAcceptApp(self.root, template_path=saved_template)

        self.assertEqual(len(app.start_btn.find_withtag("button_surface")), 1)
        self.assertEqual(app.start_btn.surface_photo.width(), 202)
        self.assertEqual(app.start_btn.surface_photo.height(), 46)


if __name__ == "__main__":
    unittest.main()
