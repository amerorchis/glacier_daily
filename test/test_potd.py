import io
import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from PIL import Image

from product_otd.product import (
    get_product,
    prepare_potd_upload,
    resize_image,
    upload_potd,
)


@pytest.fixture
def mock_graphql_response():
    """Fixture for mocking Shopify Admin GraphQL product response."""
    return {
        "data": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "handle": "test-product",
                            "title": "Test Product",
                            "description": "Detailed test description",
                            "totalInventory": 10,
                            "tracksInventory": True,
                            "seo": {"description": "Test product description"},
                            "featuredImage": {"url": "https://example.com/test.jpg"},
                        }
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }


@pytest.fixture
def mock_image():
    """Fixture for creating a mock PIL Image"""
    img = Image.new("RGB", (300, 200), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return img_byte_arr.getvalue()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set required environment variables"""
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "test.myshopify.com")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "test_token")


class TestGetProduct:
    """Test suite for get_product function"""

    def test_get_product_success(self, mock_graphql_response, mock_env_vars):
        """Test successful product retrieval"""
        mock_rng = MagicMock()
        mock_rng.randrange.return_value = 0
        with (
            patch("requests.post") as mock_post,
            patch("product_otd.product.resize_image", return_value=True),
            patch("product_otd.product.upload_potd") as mock_upload,
            patch("random.Random", return_value=mock_rng),
        ):
            mock_post.return_value = Mock(
                status_code=200,
                text=json.dumps(mock_graphql_response),
                raise_for_status=Mock(),
            )
            mock_upload.return_value = "https://example.com/uploaded.jpg"

            title, image_url, product_link, desc = get_product()

            assert title == "Test Product"
            assert image_url == "https://example.com/uploaded.jpg"
            assert product_link == "https://shop.glacier.org/products/test-product"
            assert desc == "Test product description"

    def test_get_product_image_fetch_fails(self, mock_graphql_response, mock_env_vars):
        """Test that failed image fetch returns empty tuple."""
        mock_rng = MagicMock()
        mock_rng.randrange.return_value = 0
        with (
            patch("requests.post") as mock_post,
            patch("product_otd.product.resize_image", return_value=False),
            patch("random.Random", return_value=mock_rng),
        ):
            mock_post.return_value = Mock(
                status_code=200,
                text=json.dumps(mock_graphql_response),
                raise_for_status=Mock(),
            )
            result = get_product()
            assert result == ("", "", "", "")

    def test_get_product_api_error(self, mock_env_vars):
        """Test handling of API error returns empty tuple."""
        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=500,
                raise_for_status=Mock(side_effect=requests.exceptions.HTTPError()),
            )
            result = get_product()
            assert result == ("", "", "", "")

    def test_get_product_skip_upload(self, mock_graphql_response, mock_env_vars):
        """Test get_product with skip_upload=True returns None for image."""
        mock_rng = MagicMock()
        mock_rng.randrange.return_value = 0
        with (
            patch("requests.post") as mock_post,
            patch("product_otd.product.resize_image", return_value=True),
            patch("random.Random", return_value=mock_rng),
        ):
            mock_post.return_value = Mock(
                status_code=200,
                text=json.dumps(mock_graphql_response),
                raise_for_status=Mock(),
            )
            title, image_url, product_link, _desc = get_product(skip_upload=True)
            assert title == "Test Product"
            assert image_url is None
            assert product_link == "https://shop.glacier.org/products/test-product"


class TestPreparePotdUpload:
    """Test suite for prepare_potd_upload function."""

    def test_prepare_potd_upload(self):
        """Test prepare_potd_upload returns correct tuple."""
        directory, filename, local_path = prepare_potd_upload()
        assert directory == "product"
        assert filename.endswith("_product_otd.jpg")
        assert local_path == "email_images/today/product_otd.jpg"


class TestResizeImage:
    """Test suite for resize_image function"""

    def test_resize_image_success(self, mock_image):
        """Test successful image resizing"""
        with (
            patch("requests.get") as mock_get,
            patch("product_otd.product.process_image_for_email") as mock_process,
        ):
            mock_response = Mock()
            mock_response.content = mock_image
            mock_get.return_value = mock_response

            mock_result = MagicMock()
            mock_process.return_value = mock_result

            result = resize_image("https://example.com/test.jpg")

            assert result is True
            mock_process.assert_called_once()
            mock_result.save.assert_called_once_with(
                "email_images/today/product_otd.jpg"
            )

    def test_resize_image_request_error(self):
        """Test handling of request error returns False after retries."""
        with (
            patch("requests.get") as mock_get,
            patch("shared.retry.sleep"),
        ):
            mock_get.side_effect = requests.exceptions.RequestException
            result = resize_image("https://example.com/test.jpg")
            assert result is False

    def test_resize_image_invalid_image(self):
        """Test handling of invalid image data"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"invalid image data"
            mock_get.return_value = mock_response

            with pytest.raises(OSError):
                resize_image("https://example.com/test.jpg")


class TestUploadPotd:
    """Test suite for upload_potd function"""

    def test_upload_success(self):
        """Test successful product image upload"""
        expected_url = "https://example.com/uploaded.jpg"

        mock_ftp = MagicMock()
        mock_ftp.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp.__exit__ = MagicMock(return_value=False)
        mock_ftp.upload.return_value = (expected_url, None)

        with patch("product_otd.product.FTPSession", return_value=mock_ftp):
            result = upload_potd()

            assert result == expected_url
            mock_ftp.upload.assert_called_once()

    def test_upload_error(self):
        """Test handling of upload error"""
        mock_ftp = MagicMock()
        mock_ftp.__enter__ = MagicMock(return_value=mock_ftp)
        mock_ftp.__exit__ = MagicMock(return_value=False)
        mock_ftp.upload.side_effect = Exception("Upload failed")

        with (
            patch("product_otd.product.FTPSession", return_value=mock_ftp),
            pytest.raises(Exception, match="Upload failed"),
        ):
            upload_potd()
