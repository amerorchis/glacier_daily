"""
Shared image processing utilities for email images.

Provides a standard way to prepare images for the email template:
- Resizes to fill the target width (2x display size for Retina)
- Caps height to prevent overly tall images
- Applies rounded corners and white matte for images that don't fill the frame
"""

from PIL import Image, ImageDraw


def process_image_for_email(
    image: Image.Image,
    target_width: int = 1040,
    max_height: int = 1040,
    corner_radius: int = 16,
) -> Image.Image:
    """
    Prepare an image for the email template.

    Resizes the image to fill target_width (default 1040px = 2x of 520px display).
    If the result fits within max_height, returns the resized image directly (full-bleed).
    If the image is smaller than target_width or taller than max_height, places it on
    a white canvas with rounded corners.

    Args:
        image: Source PIL Image.
        target_width: Desired pixel width (2x display width for Retina).
        max_height: Maximum pixel height before introducing a white matte.
        corner_radius: Rounded corner radius in pixels (at 2x scale).

    Returns:
        Processed PIL Image in RGB mode.
    """
    image = image.convert("RGB")
    width, height = image.size
    aspect_ratio = width / height

    # Scale to fill target width
    new_width = min(width, target_width)
    new_height = int(new_width / aspect_ratio)

    # If the image fills the target width and fits within height cap, full-bleed
    if new_width == target_width and new_height <= max_height:
        return image.resize((new_width, new_height), Image.LANCZOS)

    # Otherwise, fit within target_width x max_height and place on matte
    if new_height > max_height:
        new_height = max_height
        new_width = int(new_height * aspect_ratio)

    resized = image.resize((new_width, new_height), Image.LANCZOS)

    canvas_w = max(target_width, new_width)
    canvas_h = max(max_height, new_height)
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))

    # Apply rounded corners to the resized photo via a mask
    mask = Image.new("L", resized.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (resized.width - 1, resized.height - 1)],
        radius=corner_radius,
        fill=255,
    )

    x = (canvas_w - resized.width) // 2
    y = (canvas_h - resized.height) // 2
    canvas.paste(resized, (x, y), mask)

    return canvas
