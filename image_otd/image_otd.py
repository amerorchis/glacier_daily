"""
This module handles the image of the day functionality.
It includes functions to resize the image and upload it to a specified directory.
"""

import os
import sys
from datetime import datetime

from PIL import Image
from dotenv import load_dotenv
load_dotenv("email.env")

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from image_otd.flickr import get_flickr
from shared.retrieve_from_json import retrieve_from_json
from shared.ftp import upload_file


def upload_pic_otd():
    """
    Upload the picture of the day to the specified directory.

    Returns:
        str: The address where the image was uploaded.
    """
    today = datetime.now()
    filename = f'{today.month}_{today.day}_{today.year}_pic_otd.jpg'
    file = 'email_images/today/resized_image_otd.jpg'
    directory = 'picture'
    address, _ = upload_file(directory, filename, file)
    return address

def resize_full():
    """
    Resize the image of the day to the desired dimensions and upload it.

    Returns:
        tuple: A tuple containing the upload address, title, and link of the image.
    """
    # Check if we already have today's image
    already_retrieved, keys = retrieve_from_json(['image_otd', 'image_otd_title', 'image_otd_link'])
    if already_retrieved:
        return keys

    # If no image exists for today, proceed with getting and resizing new image
    image_path, title, link = get_flickr()
    image = Image.open(image_path)

    scale_multiplier = 4
    desired_width = 255 * scale_multiplier
    desired_height = 150 * scale_multiplier
    width, height = image.size

    # Calculate the aspect ratio of the image
    aspect_ratio = width / height

    # Calculate the new width and height to fill the canvas
    if width / desired_width > height / desired_height:
        new_width = desired_width
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = desired_height
        new_width = int(new_height * aspect_ratio)

    # Resize the image while maintaining the aspect ratio
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)

    # Create a new white background image with the desired dimensions
    canvas = Image.new('RGB', (desired_width, desired_height), (255, 255, 255))

    # Calculate the position to paste the resized image and center it
    x = (canvas.width - resized_image.width) // 2
    y = (canvas.height - resized_image.height) // 2

    # Paste the resized image onto the canvas
    canvas.paste(resized_image, (x, y))

    # Save the final image
    canvas.save('email_images/today/resized_image_otd.jpg')

    return upload_pic_otd(), title, link

if __name__ == "__main__":
    print(resize_full())
