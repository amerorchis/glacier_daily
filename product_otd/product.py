"""
Select a product at random, find its image, resize and upload the image,
then return a description, link to product, and link to photo.
"""

import json
import random
from io import BytesIO
from re import sub

import requests
from PIL import Image

from shared.datetime_utils import now_mountain
from shared.ftp import upload_file
from shared.image_utils import process_image_for_email
from shared.settings import get_settings


def prepare_potd_upload() -> tuple[str, str, str]:
    """Return (directory, filename, local_path) for product image upload."""
    today = now_mountain()
    filename = f"{today.month}_{today.day}_{today.year}_product_otd.jpg"
    return "product", filename, "email_images/today/product_otd.jpg"


def upload_potd():
    """
    Upload the product image to the glacier.org ftp server.
    """
    directory, filename, local_path = prepare_potd_upload()
    address, _ = upload_file(directory, filename, local_path)
    return address


def resize_image(url):
    """
    Fetch a product image and process it for the email template.
    """
    response = requests.get(url, timeout=5)
    image = Image.open(BytesIO(response.content))
    result = process_image_for_email(image)
    result.save("email_images/today/product_otd.jpg")


def get_product(skip_upload: bool = False):
    """
    Grab a random product from the BigCommerce API.
    """
    # Connect to API
    settings = get_settings()
    url = (
        f"https://api.bigcommerce.com/stores/{settings.BC_STORE_HASH}/v3/catalog/products?"
        "inventory_level:min=1&is_visible=true"
    )
    header = {
        "X-Auth-Token": settings.BC_TOKEN,
    }

    # Figure out total number of products
    r = requests.get(url=url, headers=header, timeout=12)
    if r.status_code == 500:
        raise requests.exceptions.RequestException

    products = json.loads(r.text)
    total_products = products["meta"]["pagination"]["total"]

    # Select one of these products
    random.seed(now_mountain().strftime("%Y:%m:%d"))
    product_otd = random.randrange(1, total_products + 1)  # noqa: S311

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
            f"https://api.bigcommerce.com/stores/{settings.BC_STORE_HASH}/v3/catalog/products?"
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
            f"https://api.bigcommerce.com/stores/{settings.BC_STORE_HASH}/v3/catalog/products/"
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
    for _attempt in range(50):
        try:
            product_data = retrieve_potd(product_otd)
            if product_data["image_url"]:
                break
            else:
                raise ValueError("Product not found")

        except (ValueError, IndexError, KeyError):
            product_otd = random.randint(1, total_products)  # noqa: S311
    else:
        # All attempts exhausted without finding a product with an image
        return ("", "", "", "")

    # Resize and upload the image retrieved
    resize_image(product_data["image_url"])

    image_url = None if skip_upload else upload_potd()

    return (
        product_data["name"],
        image_url,
        product_data["product_link"],
        product_data["desc"],
    )


if __name__ == "__main__":  # pragma: no cover
    print(get_product())
