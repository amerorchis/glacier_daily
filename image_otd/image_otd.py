"""
This module handles the image of the day functionality.
It includes functions to resize the image and upload it to a specified directory.
"""

from pathlib import Path

from PIL import Image, UnidentifiedImageError

from image_otd.flickr import FlickrAPIError, get_flickr
from shared.datetime_utils import now_mountain
from shared.ftp import FTPSession
from shared.image_utils import process_image_for_email


class ImageProcessingError(Exception):
    """Raised when image processing operations fail"""

    pass


def prepare_pic_otd() -> tuple[str, str, str]:
    """Return (directory, filename, local_path) for the picture of the day upload."""
    today = now_mountain()
    filename = f"{today.month}_{today.day}_{today.year}_pic_otd.jpg"
    file = Path("email_images/today/resized_image_otd.jpg")

    if not file.exists():
        raise FileNotFoundError(f"Image file not found: {file}")

    return "picture", filename, str(file)


def upload_pic_otd() -> str:
    """
    Upload the picture of the day to the specified directory.

    Returns:
        str: The address where the image was uploaded

    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    directory, filename, local_path = prepare_pic_otd()
    with FTPSession() as ftp:
        address, _ = ftp.upload(directory, filename, local_path)
    return address


def process_image(image_path: Path) -> Path:
    """
    Process and resize an image for the email template.

    Resizes to fill the email content width (2x for Retina), with a 1:1 height cap.
    Images that don't fill the frame get a white matte with rounded corners.

    Args:
        image_path: Path to the input image

    Returns:
        Path: Path to the processed image

    Raises:
        ImageProcessingError: If image processing fails
    """
    try:
        image = Image.open(image_path)
        result = process_image_for_email(image)

        output_path = Path("email_images/today/resized_image_otd.jpg")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)

        return output_path

    except UnidentifiedImageError as e:
        raise ImageProcessingError("Invalid or corrupt image file") from e
    except Exception as e:
        raise ImageProcessingError(f"Image processing failed: {str(e)}") from e


def resize_full(skip_upload: bool = False) -> tuple[str | None, str, str]:
    """
    Main function to retrieve and process the image of the day.

    Returns:
        tuple[str, str, str]: (upload_address, image_title, image_link)

    Raises:
        FlickrAPIError: If Flickr operations fail
        ImageProcessingError: If image processing fails
    """
    image_data = get_flickr()
    process_image(image_data.path)

    if skip_upload:
        return None, image_data.title, image_data.link

    upload_address = upload_pic_otd()
    return upload_address, image_data.title, image_data.link


def get_image_otd(skip_upload: bool = False) -> tuple[str | None, str, str]:
    """
    Get the image of the day from Flickr.
    """
    try:
        return resize_full(skip_upload=skip_upload)
    except FlickrAPIError:
        return "", "", ""


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
