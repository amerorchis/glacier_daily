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
    return {"data": [{"url_zoom": "https://example.com/test.jpg"}]}


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
        with (
            patch("requests.get") as mock_get,
            patch("product_otd.product.resize_image"),
            patch("product_otd.product.upload_potd") as mock_upload,
            patch("random.randrange", return_value=1),
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

    def test_get_product_api_error(self, mock_env_vars):
        """Test handling of API error"""
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=500)

            with pytest.raises(requests.exceptions.RequestException):
                get_product()

    def test_get_product_skip_upload(
        self, mock_product_response, mock_image_response, mock_env_vars
    ):
        """Test get_product with skip_upload=True returns None for image."""
        with (
            patch("requests.get") as mock_get,
            patch("product_otd.product.resize_image"),
            patch("random.randrange", return_value=1),
        ):
            mock_get.side_effect = [
                Mock(status_code=200, text=json.dumps(mock_product_response)),
                Mock(status_code=200, text=json.dumps(mock_product_response)),
                Mock(status_code=200, text=json.dumps(mock_image_response)),
            ]
            title, image_url, product_link, desc = get_product(skip_upload=True)
            assert title == "Test Product"
            assert image_url is None
            assert product_link == "https://shop.glacier.org/test-product"


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

            resize_image("https://example.com/test.jpg")

            mock_process.assert_called_once()
            mock_result.save.assert_called_once_with(
                "email_images/today/product_otd.jpg"
            )

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


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
