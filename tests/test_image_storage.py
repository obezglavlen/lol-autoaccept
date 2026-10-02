import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from image_storage import (
    default_template_path,
    first_supported_drop_path,
    persist_template,
)


class PersistTemplateTests(unittest.TestCase):
    def test_persist_template_survives_when_source_is_removed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source = temp_path / "source.jpg"
            destination = temp_path / "saved" / "accept_template.png"
            Image.new("RGB", (4, 3), (12, 34, 56)).save(source, quality=100)

            result = persist_template(source, destination)
            source.unlink()

            self.assertEqual(result, destination)
            self.assertTrue(destination.is_file())
            with Image.open(destination) as saved:
                self.assertEqual(saved.size, (4, 3))
                self.assertEqual(saved.format, "PNG")

    def test_default_template_path_uses_local_app_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}):
                expected = Path(temp_dir) / "LoLAutoAccept" / "accept_template.png"
                self.assertEqual(default_template_path(), expected)

    def test_drop_path_parser_accepts_an_image_path_with_spaces(self):
        def split_tcl_list(_value):
            return ("C:/Images/accept button.PNG", "C:/Images/readme.txt")

        result = first_supported_drop_path("raw drop data", split_tcl_list)

        self.assertEqual(result, Path("C:/Images/accept button.PNG"))


if __name__ == "__main__":
    unittest.main()
