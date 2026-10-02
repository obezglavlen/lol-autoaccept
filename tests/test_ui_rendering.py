import unittest

from main import render_rounded_rectangle_image


class RoundedSurfaceRenderingTests(unittest.TestCase):
    def test_rounded_surface_contains_antialiased_edge_pixels(self):
        image = render_rounded_rectangle_image(
            width=80,
            height=40,
            radius=20,
            fill="#0071e3",
        )

        alpha_histogram = image.getchannel("A").histogram()

        self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertEqual(image.getpixel((40, 20))[3], 255)
        self.assertTrue(any(alpha_histogram[1:255]))


if __name__ == "__main__":
    unittest.main()
