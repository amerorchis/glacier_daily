"""Tests for shared.image_utils module."""

from PIL import Image

from shared.image_utils import process_image_for_email


class TestProcessImageForEmail:
    """Test suite for process_image_for_email."""

    def test_landscape_fills_width(self):
        """A wide landscape image should resize to fill target width."""
        img = Image.new("RGB", (2000, 1000))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        assert result.size == (1040, 520)

    def test_portrait_within_cap(self):
        """A portrait image within the height cap should fill width."""
        img = Image.new("RGB", (1500, 2000))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        # 1040 wide / (1500/2000) = 1040 / 0.75 = 1386 > 1040 cap
        # So it should get the matte treatment at 1040x1040
        assert result.size == (1040, 1040)

    def test_tall_portrait_gets_matte(self):
        """A very tall portrait should be capped and placed on a white matte."""
        img = Image.new("RGB", (500, 2000))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        assert result.size == (1040, 1040)

    def test_small_image_upscaled_to_fill(self):
        """An image smaller than target_width should be upscaled to fill."""
        img = Image.new("RGB", (400, 300))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        # 400x300 (4:3) → upscaled to 1040x780, fits within cap
        assert result.size == (1040, 780)
        assert result.mode == "RGB"

    def test_exact_width_match(self):
        """An image exactly at target width should resize correctly."""
        img = Image.new("RGB", (1040, 600))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        assert result.size == (1040, 600)

    def test_square_image_at_cap(self):
        """A square image exactly at 1:1 should fill width and height."""
        img = Image.new("RGB", (2000, 2000))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        assert result.size == (1040, 1040)

    def test_rgba_converted_to_rgb(self):
        """An RGBA image should be converted to RGB."""
        img = Image.new("RGBA", (2000, 1000), (255, 0, 0, 128))
        result = process_image_for_email(img)

        assert result.mode == "RGB"

    def test_custom_dimensions(self):
        """Custom target_width and max_height should be respected."""
        img = Image.new("RGB", (2000, 1000))
        result = process_image_for_email(img, target_width=800, max_height=600)

        assert result.size == (800, 400)

    def test_matte_is_white(self):
        """The matte canvas should be white for tall portrait images."""
        # Very tall portrait — will hit the matte path
        img = Image.new("RGB", (500, 2000), (255, 0, 0))
        result = process_image_for_email(img, target_width=1040, max_height=1040)

        # Top-left corner should be white (part of the matte, outside the photo)
        assert result.getpixel((0, 0)) == (255, 255, 255)
