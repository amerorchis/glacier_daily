"""
This module handles the creation and uploading of weather images for Glacier National Park.

The module creates weather maps with temperature and condition overlays for various
locations within the park, then uploads them to an FTP server.
"""

from PIL import Image, ImageDraw, ImageFont

from shared.datetime_utils import format_date_readable, now_mountain
from shared.ftp import FTPSession
from weather.season import get_season
from weather.weather import weather_data

# Constants
DIMENSIONS: dict[str, tuple[float, float]] = {
    "West Glacier": (292.1848, 462.5),
    "Polebridge": (165.3, 190),
    "St. Mary": (591, 303),
    "Two Medicine": (623, 524),
    "Logan Pass": (423.52, 336),
    "Many Glacier": (460.1623, 185),
}


def prepare_weather_upload() -> tuple[str, str, str]:
    """Return (directory, filename, local_path) for weather image upload."""
    today = now_mountain()
    filename = f"{today.month}_{today.day}_{today.year}_today_park_map.png"
    return "weather", filename, "email_images/today/today_park_map.png"


def upload_weather() -> str:
    """
    Upload the weather image to the glacier.org ftp server.

    Returns:
        str: Address of the uploaded image.
    """
    directory, filename, local_path = prepare_weather_upload()
    with FTPSession() as ftp:
        address, _ = ftp.upload(directory, filename, local_path)
    return address


def _validate_input(results: list[tuple[str, int, int, str]]) -> None:
    """Validate the input data format and values."""
    if not results:
        raise ValueError("Results list cannot be empty")

    for location in results:
        if len(location) != 4:
            raise ValueError(
                "Each location must have name, high temp, low temp, and condition"
            )
        name, high, low, cond = location
        if name not in DIMENSIONS:
            raise ValueError(f"Unknown location: {name}")
        if not isinstance(high, int) or not isinstance(low, int):
            raise ValueError(f"Temperatures must be integers for {name}")
        if not cond:
            raise ValueError(f"Weather condition cannot be empty for {name}")


def _get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Get font object with error handling."""
    try:
        return ImageFont.truetype(font_path, size)
    except OSError as e:
        raise FileNotFoundError(f"Font file not found or invalid: {font_path}") from e


def _get_base_image(season: str) -> Image.Image:
    """Get the base map image for the given season."""
    image_path = f"email_images/base/park_map_{season}.png"
    try:
        return Image.open(image_path)
    except OSError as e:
        raise FileNotFoundError(f"Base map not found: {image_path}") from e


def weather_image(
    results: list[tuple[str, int, int, str]], skip_upload: bool = False
) -> str | None:
    """
    Create a weather image based on the provided forecast results and upload it.

    Args:
        results (list[tuple[str, int, int, str]]): list of tuples containing location
            name, high temperature, low temperature, and weather condition.

    Returns:
        str: Address of the uploaded image.
    """
    _validate_input(results)

    # Get base image
    image = _get_base_image(get_season())
    draw = ImageDraw.Draw(image)

    # Setup font
    font_path = "email_images/base/OpenSans-Regular.ttf"
    default_font = _get_font(font_path, 20)

    # Add weather data for each location
    for location in results:
        name, high, low, cond = location
        left, y = DIMENSIONS[name]

        # Add temperature
        temp_text = f"{high} | {low}"
        text_width = draw.textlength(temp_text, font=default_font)
        x = left + ((139.11 - text_width) / 2)
        draw.text((x, y), temp_text, font=default_font, fill=(0, 0, 0))

        # Add condition with dynamic font sizing
        font_size = 20
        condition_font = default_font
        text_width = draw.textlength(cond, font=condition_font)

        while text_width > 139.11 and font_size > 10:
            font_size -= 1
            condition_font = _get_font(font_path, font_size)
            text_width = draw.textlength(cond, font=condition_font)

        x = left + ((139.11 - text_width) / 2)
        draw.text((x, y + 24), cond, font=condition_font, fill=(0, 0, 0))

    # Add date
    day = format_date_readable(now_mountain()).upper()
    text_width = draw.textlength(day, font=default_font)
    x = 149 + ((347 - text_width) / 2)
    draw.text((x, 74), day, font=default_font, fill="#FFFFFF")

    # Save and resize
    try:
        image = image.resize((810, 748), Image.Resampling.LANCZOS)
        image.save("email_images/today/today_park_map.png")
    except OSError as e:
        raise OSError(f"Failed to save image: {e}") from e

    if skip_upload:
        return None
    return upload_weather()


if __name__ == "__main__":  # pragma: no cover
    print(weather_image(weather_data().forecasts or []))
