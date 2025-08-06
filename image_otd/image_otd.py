"""
This module handles the image of the day functionality.
It includes functions to resize the image and upload it to a specified directory.
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

load_dotenv("email.env")

from image_otd.flickr import FlickrAPIError, get_flickr
from shared.ftp import upload_file
from shared.retrieve_from_json import retrieve_from_json


class ImageProcessingError(Exception):
    """Raised when image processing operations fail"""

    pass


def upload_pic_otd() -> str:
    """
    Upload the picture of the day to the specified directory.

    Returns:
        str: The address where the image was uploaded

    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    today = datetime.now()
    filename = f"{today.month}_{today.day}_{today.year}_pic_otd.jpg"
    file = Path("email_images/today/resized_image_otd.jpg")

    if not file.exists():
        raise FileNotFoundError(f"Image file not found: {file}")

    directory = "picture"
    address, _ = upload_file(directory, filename, str(file))
    return address


def process_image(image_path: Path, dimensions: Tuple[int, int, int]) -> Path:
    """
    Process and resize an image while maintaining aspect ratio.

    Args:
        image_path: Path to the input image
        dimensions: Tuple of (width, height, scale_multiplier)

    Returns:
        Path: Path to the processed image

    Raises:
        ImageProcessingError: If image processing fails
    """
    try:
        desired_width, desired_height, scale_multiplier = dimensions
        desired_width *= scale_multiplier
        desired_height *= scale_multiplier

        image = Image.open(image_path)
        width, height = image.size

        aspect_ratio = width / height
        if width / desired_width > height / desired_height:
            new_width = desired_width
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = desired_height
            new_width = int(new_height * aspect_ratio)

        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        canvas = Image.new("RGB", (desired_width, desired_height), (255, 255, 255))

        x = (canvas.width - resized_image.width) // 2
        y = (canvas.height - resized_image.height) // 2
        canvas.paste(resized_image, (x, y))

        output_path = Path("email_images/today/resized_image_otd.jpg")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)

        return output_path

    except UnidentifiedImageError:
        raise ImageProcessingError("Invalid or corrupt image file")
    except Exception as e:
        raise ImageProcessingError(f"Image processing failed: {str(e)}")


def resize_full() -> Tuple[str, str, str]:
    """
    Main function to retrieve and process the image of the day.

    Returns:
        Tuple[str, str, str]: (upload_address, image_title, image_link)

    Raises:
        FlickrAPIError: If Flickr operations fail
        ImageProcessingError: If image processing fails
    """
    already_retrieved, keys = retrieve_from_json(
        ["image_otd", "image_otd_title", "image_otd_link"]
    )
    if already_retrieved:
        return keys

    image_data = get_flickr()
    dimensions = (255, 150, 4)  # width, height, scale_multiplier
    process_image(image_data.path, dimensions)
    upload_address = upload_pic_otd()

    return upload_address, image_data.title, image_data.link


def get_image_otd() -> Tuple[str, str, str]:
    """
    Get the image of the day from Flickr.
    """
    try:
        return resize_full()
    except FlickrAPIError:
        return "Flickr API Error", "", ""


if __name__ == "__main__":
    try:
        upload_address, image_title, image_link = resize_full()
        print(f"Image uploaded to: {upload_address}")
        print(f"Image title: {image_title}")
        print(f"Image link: {image_link}")
    except (FileNotFoundError, ImageProcessingError) as e:
        print(f"Error processing image: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        # traceback.print_exc()
