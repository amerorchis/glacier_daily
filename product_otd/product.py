"""
Select a product at random, find its image, resize and upload the image,
then return a description, link to product, and link to photo.
"""

import json
import random
from io import BytesIO

import requests
from PIL import Image

from shared.datetime_utils import now_mountain
from shared.ftp import FTPSession
from shared.image_utils import process_image_for_email
from shared.logging_config import get_logger
from shared.retry import retry
from shared.settings import get_settings

logger = get_logger(__name__)

SHOPIFY_API_VERSION = "2024-10"
SHOPIFY_PAGE_SIZE = 250
MAX_PAGES = 20
PRODUCT_DESC_MAX_LEN = 150
MAX_PRODUCT_SEARCH_ATTEMPTS = 50
SHOP_DOMAIN = "https://shop.glacier.org"

PRODUCTS_QUERY = f"""
query Products($cursor: String) {{
  products(first: {SHOPIFY_PAGE_SIZE}, after: $cursor, query: "status:active") {{
    edges {{
      node {{
        handle
        title
        description
        totalInventory
        tracksInventory
        seo {{ description }}
        featuredImage {{ url }}
      }}
    }}
    pageInfo {{ hasNextPage endCursor }}
  }}
}}
"""


def prepare_potd_upload() -> tuple[str, str, str]:
    """Return (directory, filename, local_path) for product image upload."""
    today = now_mountain()
    filename = f"{today.month}_{today.day}_{today.year}_product_otd.jpg"
    return "product", filename, "email_images/today/product_otd.jpg"


def upload_potd() -> str:
    """
    Upload the product image to the glacier.org ftp server.
    """
    directory, filename, local_path = prepare_potd_upload()
    with FTPSession() as ftp:
        address, _ = ftp.upload(directory, filename, local_path)
    return address


@retry(2, (requests.exceptions.RequestException,), default=False, backoff=5)
def resize_image(url) -> bool:
    """
    Fetch a product image and process it for the email template.

    Returns:
        True on success, False after retries are exhausted.
    """
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    result = process_image_for_email(image)
    result.save("email_images/today/product_otd.jpg")
    return True


def _clean_description(raw: str) -> str:
    """Trim a product description to PRODUCT_DESC_MAX_LEN characters."""
    desc = raw.replace("&nbsp;", "").strip()
    if len(desc) > PRODUCT_DESC_MAX_LEN:
        cut = desc.find(" ", PRODUCT_DESC_MAX_LEN)
        if cut == -1:
            cut = PRODUCT_DESC_MAX_LEN
        desc = desc[:cut] + "..."
    return desc


def _fetch_eligible_products(endpoint: str, headers: dict) -> list[dict]:
    """Walk Storefront pagination and return all in-stock published products."""
    products: list[dict] = []
    cursor: str | None = None

    for _ in range(MAX_PAGES):
        body = {"query": PRODUCTS_QUERY, "variables": {"cursor": cursor}}
        r = requests.post(endpoint, headers=headers, json=body, timeout=12)
        r.raise_for_status()
        payload = json.loads(r.text)

        if payload.get("errors"):
            raise ValueError(f"Shopify GraphQL errors: {payload['errors']}")

        connection = payload["data"]["products"]
        products.extend(edge["node"] for edge in connection["edges"])

        page_info = connection["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return products


def _build_product_data(node: dict) -> dict | None:
    """Convert a Shopify product node into our internal dict.

    Returns None if the product is missing an image or is out of stock.
    Products that don't track inventory are treated as always available.
    """
    featured = node.get("featuredImage")
    if not featured or not featured.get("url"):
        return None

    if node.get("tracksInventory") and (node.get("totalInventory") or 0) <= 0:
        return None

    seo = node.get("seo") or {}
    raw_desc = seo.get("description") or node.get("description") or ""

    return {
        "image_url": featured["url"],
        "name": node["title"],
        "desc": _clean_description(raw_desc),
        "product_link": f"{SHOP_DOMAIN}/products/{node['handle']}",
    }


def get_product(skip_upload: bool = False) -> tuple[str, str | None, str, str]:
    """
    Grab a random product from the Shopify Storefront API.
    """
    settings = get_settings()
    endpoint = f"https://{settings.SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }

    try:
        products = _fetch_eligible_products(endpoint, headers)
    except (
        requests.exceptions.RequestException,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as e:
        logger.error("Unexpected Shopify product list response: %s", e)
        return ("", "", "", "")

    if not products:
        logger.error("Shopify returned no eligible products")
        return ("", "", "", "")

    rng = random.Random(now_mountain().strftime("%Y:%m:%d"))  # noqa: S311

    product_data: dict | None = None
    for _ in range(MAX_PRODUCT_SEARCH_ATTEMPTS):
        node = products[rng.randrange(len(products))]
        product_data = _build_product_data(node)
        if product_data is not None:
            break
    else:
        return ("", "", "", "")

    if not resize_image(product_data["image_url"]):
        logger.error("Failed to fetch product image")
        return ("", "", "", "")

    image_url = None if skip_upload else upload_potd()

    return (
        product_data["name"],
        image_url,
        product_data["product_link"],
        product_data["desc"],
    )


if __name__ == "__main__":  # pragma: no cover
    print(get_product())
