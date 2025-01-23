"""
Select a product at random, find its image, resize and upload the image, 
then return a description, link to product, and link to photo.
"""

import sys
import json
import os
import random

from re import sub
from datetime import datetime
from io import BytesIO
import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv("email.env")

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from shared.retrieve_from_json import retrieve_from_json
from shared.ftp import upload_file


def upload_potd():
    """
    Upload the product image to the glacier.org ftp server.
    """
    today = datetime.now()
    filename = f"{today.month}_{today.day}_{today.year}_product_otd.jpg"
    file = "email_images/today/product_otd.jpg"
    directory = "product"
    address, _ = upload_file(directory, filename, file)
    return address


def resize_image(url):
    """
    Put the image on a white matte, resized to fit email.
    """
    # Fetch the image from the URL
    response = requests.get(url, timeout=5)
    image = Image.open(BytesIO(response.content))

    # Calculate the new size while maintaining the aspect ratio
    width, height = image.size
    aspect_ratio = width / height

    # Calculate the new width and height to fit within the canvas
    scale_multiplier = 2
    new_width = min(width, 255 * scale_multiplier)
    new_height = int(new_width / aspect_ratio)

    # Check if the new height exceeds the canvas height
    if new_height > (150 * scale_multiplier):
        new_height = 150 * scale_multiplier
        new_width = int(new_height * aspect_ratio)

    # Resize the image
    resized_image = image.resize((new_width, new_height))

    # Create a new blank canvas with white background
    canvas = Image.new("RGB", (255 * scale_multiplier, 150 * scale_multiplier), "white")

    # Calculate the position to paste the resized image
    x = (canvas.width - resized_image.width) // 2
    y = (canvas.height - resized_image.height) // 2

    # Paste the resized image onto the canvas
    canvas.paste(resized_image, (x, y))

    # Save or display the resulting image
    canvas.save("email_images/today/product_otd.jpg")


def get_product():
    """
    Grab a random product from the BigCommerce API.
    """
    already_retrieved, keys = retrieve_from_json(
        ["product_title", "product_image", "product_link", "product_desc"]
    )
    if already_retrieved:
        return keys

    # Connect to API
    bc_token = os.environ["BC_TOKEN"]
    store_hash = os.environ["BC_STORE_HASH"]
    url = (
        f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products?"
        "inventory_level:min=1&is_visible=true"
    )
    header = {
        "X-Auth-Token": bc_token,
    }

    # Figure out total number of products
    r = requests.get(url=url, headers=header, timeout=12)
    if r.status_code == 500:
        raise requests.exceptions.RequestException

    products = json.loads(r.text)
    total_products = products["meta"]["pagination"]["total"]

    # Select one of these products
    random.seed(datetime.today().strftime("%Y:%m:%d"))
    product_otd = random.randrange(1, total_products + 1)

    # Function to retrieve a product.
    def retrieve_potd(product_otd):
        """
        Retrieve a product at a given index, parse out a description and grab the image url.
        """
        # Calculate the page and index of the random product.
        product_page = product_otd // 50 + 1
        product_index = product_otd % 50 - 1

        # Retrieve item from response.
        new_url = (
            f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products?"
            f"inventory_level:min=1&is_visible=true&page={product_page}"
        )
        r = requests.get(url=new_url, headers=header, timeout=12)
        products = json.loads(r.text)
        item = products["data"][product_index]
        name = item["name"]

        # Match instances of multiple line breaks and reduce them to a single <br>
        desc = (
            item["meta_description"]
            if item["meta_description"]
            else item["description"]
        )
        pattern = r"(<(?!br\s*\/?)[^>]*>)|((<br\s*\/?>)\s*)+"
        desc = sub(pattern, lambda m: m.group(1) if m.group(1) else "<br>", desc)

        desc = desc.replace("&nbsp;", "")  # remove non-breaking spaces
        desc = sub(r"<p[^>]*>|<\/p>", "", desc)  # remove paragraph tags
        desc = sub(r"(?<=\w)(\.)", r"\1 ", desc)  # add space after sentence
        desc = sub(r"<div[^>]*>|<\/div>", "", desc).strip()  # remove div tags

        # Truncate long descriptions
        if len(desc) > 150:
            index = desc.find(" ", 150)
            desc = desc[:index] + "..."

        # Get image url
        item_url = f"https://shop.glacier.org{item['custom_url']['url']}"
        get_image_url = (
            f"https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/"
            f"{item['id']}/images"
        )
        r = requests.get(url=get_image_url, headers=header, timeout=12)
        image_url = json.loads(r.text)["data"][0]["url_standard"]

        return {
            "image_url": image_url,
            "name": name,
            "desc": desc,
            "product_link": item_url,
        }

    # Keep searching for products if they don't have images.
    while True:
        try:
            product_data = retrieve_potd(product_otd)
            if product_data["image_url"]:
                break
            else:
                raise ValueError("Product not found")

        except ValueError:
            product_otd = random.randint(1, total_products)

    # Resize and upload the image retrieved
    resize_image(product_data["image_url"])
    image_url = upload_potd()

    return (
        product_data["name"],
        image_url,
        product_data["product_link"],
        product_data["desc"],
    )


if __name__ == "__main__":
    print(get_product())
