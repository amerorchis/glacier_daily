import io
import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from PIL import Image

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover

from product_otd.product import get_product, resize_image, upload_potd


@pytest.fixture
def mock_product_response():
    """Fixture for mocking BigCommerce API product response"""
    return {
        "data": [
            {
                "id": 1,
                "name": "Test Product",
                "custom_url": {"url": "/test-product"},
                "meta_description": "Test product description",
                "description": "Detailed test description",
            }
        ],
        "meta": {"pagination": {"total": 50}},
    }


@pytest.fixture
def mock_image_response():
    """Fixture for mocking BigCommerce API image response"""
    return {"data": [{"url_standard": "https://example.com/test.jpg"}]}


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
    monkeypatch.setenv("BC_TOKEN", "test_token")
    monkeypatch.setenv("BC_STORE_HASH", "test_store")


class TestGetProduct:
    """Test suite for get_product function"""

    def test_get_product_success(
        self, mock_product_response, mock_image_response, mock_env_vars
    ):
        """Test successful product retrieval"""
        with patch("requests.get") as mock_get, patch(
            "product_otd.product.resize_image"
        ) as mock_resize, patch(
            "product_otd.product.upload_potd"
        ) as mock_upload, patch(
            "product_otd.product.retrieve_from_json", return_value=(False, None)
        ), patch(
            "random.randrange", return_value=1
        ):

            # Mock API responses
            mock_get.side_effect = [
                Mock(status_code=200, text=json.dumps(mock_product_response)),
                Mock(status_code=200, text=json.dumps(mock_product_response)),
                Mock(status_code=200, text=json.dumps(mock_image_response)),
            ]
            mock_upload.return_value = "https://example.com/uploaded.jpg"

            title, image_url, product_link, desc = get_product()
            print(title, image_url, product_link, desc)

            assert title == "Test Product"
            assert image_url == "https://example.com/uploaded.jpg"
            assert product_link == "https://shop.glacier.org/test-product"
            assert desc == "Test product description"

    def test_get_product_cached(self):
        """Test product retrieval from cache"""
        cached_data = (
            "Test Product",
            "https://example.com/img.jpg",
            "https://shop.glacier.org/test",
            "Cached description",
        )

        with patch(
            "product_otd.product.retrieve_from_json", return_value=(True, cached_data)
        ):
            title, image_url, product_link, desc = get_product()

            assert title == cached_data[0]
            assert image_url == cached_data[1]
            assert product_link == cached_data[2]
            assert desc == cached_data[3]

    def test_get_product_api_error(self, mock_env_vars):
        """Test handling of API error"""
        with patch("requests.get") as mock_get, patch(
            "product_otd.product.retrieve_from_json", return_value=(False, None)
        ):

            mock_get.return_value = Mock(status_code=500)

            with pytest.raises(requests.exceptions.RequestException):
                get_product()


class TestResizeImage:
    """Test suite for resize_image function"""

    def test_resize_image_success(self, mock_image):
        """Test successful image resizing"""
        with patch("requests.get") as mock_get, patch(
            "PIL.Image.open"
        ) as mock_open, patch("PIL.Image.new") as mock_new:

            # Mock request response
            mock_response = Mock()
            mock_response.content = mock_image
            mock_get.return_value = mock_response

            # Mock PIL Image operations
            mock_img = MagicMock()
            mock_img.size = (300, 200)
            mock_open.return_value = mock_img
            mock_new.return_value = mock_img

            resize_image("https://example.com/test.jpg")

            # Verify image was processed
            mock_img.resize.assert_called_once()
            mock_img.save.assert_called_once()

    def test_resize_image_request_error(self):
        """Test handling of request error"""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException

            with pytest.raises(requests.exceptions.RequestException):
                resize_image("https://example.com/test.jpg")

    def test_resize_image_invalid_image(self):
        """Test handling of invalid image data"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = b"invalid image data"
            mock_get.return_value = mock_response

            with pytest.raises(Exception):
                resize_image("https://example.com/test.jpg")


class TestUploadPotd:
    """Test suite for upload_potd function"""

    def test_upload_success(self):
        """Test successful product image upload"""
        expected_url = "https://example.com/uploaded.jpg"

        with patch("product_otd.product.upload_file") as mock_upload:
            mock_upload.return_value = (expected_url, None)

            result = upload_potd()

            assert result == expected_url
            mock_upload.assert_called_once()

    def test_upload_error(self):
        """Test handling of upload error"""
        with patch("product_otd.product.upload_file") as mock_upload:
            mock_upload.side_effect = Exception("Upload failed")

            with pytest.raises(Exception, match="Upload failed"):
                upload_potd()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
