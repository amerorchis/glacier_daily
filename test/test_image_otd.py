# test_flickr.py
import sys
import os

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from PIL import Image, UnidentifiedImageError


if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from image_otd.flickr import FlickrImage, get_flickr, FlickrAPIError
from image_otd.image_otd import (
    process_image,
    resize_full,
    upload_pic_otd,
    ImageProcessingError,
)


@pytest.fixture
def mock_env_vars():
    env_vars = {
        "flickr_key": "test_key",
        "flickr_secret": "test_secret",
        "glaciernps_uid": "test_uid",
    }
    with patch.dict("os.environ", env_vars):
        yield env_vars


@pytest.fixture
def mock_flickr_response():
    return {
        "photos": {
            "total": "100",
            "photo": [
                {
                    "server": "test_server",
                    "id": "test_id",
                    "secret": "test_secret",
                    "title": "test_title",
                }
            ],
        }
    }


def test_get_flickr_success(mock_env_vars, mock_flickr_response):
    with patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI, patch(
        "image_otd.flickr.urlretrieve"
    ) as mock_urlretrieve:

        # Setup mock FlickrAPI
        mock_api = Mock()
        mock_api.photos.search.return_value = mock_flickr_response
        MockFlickrAPI.return_value = mock_api

        # Setup mock urlretrieve
        mock_urlretrieve.return_value = None

        result = get_flickr()

        assert isinstance(result, FlickrImage)
        assert result.title == "test_title"
        assert result.link == "https://flickr.com/photos/glaciernps/test_id"
        assert isinstance(result.path, Path)


def test_get_flickr_missing_env_var():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(FlickrAPIError, match="Missing environment variable"):
            get_flickr()


def test_get_flickr_api_error(mock_env_vars):
    with patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI:
        mock_api = Mock()
        mock_api.photos.search.side_effect = Exception("API Error")
        MockFlickrAPI.return_value = mock_api

        with pytest.raises(FlickrAPIError, match="Flickr API error"):
            get_flickr()


def test_get_flickr_download_error(mock_env_vars, mock_flickr_response):
    with patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI, patch(
        "image_otd.flickr.urlretrieve"
    ) as mock_urlretrieve:

        mock_api = Mock()
        mock_api.photos.search.return_value = mock_flickr_response
        MockFlickrAPI.return_value = mock_api

        mock_urlretrieve.side_effect = URLError("Download failed")

        with pytest.raises(FlickrAPIError, match="Failed to download image"):
            get_flickr()


# test/test_image_otd.py
import pytest
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from unittest.mock import Mock, patch

from image_otd.flickr import FlickrImage
from image_otd.image_otd import (
    process_image,
    resize_full,
    upload_pic_otd,
    ImageProcessingError,
)


@pytest.fixture
def sample_image(tmp_path):
    # Create a test image
    img_path = tmp_path / "test.jpg"
    image = Image.new("RGB", (800, 600), color="white")
    image.save(img_path)
    return img_path


def test_process_image_success(sample_image, tmp_path):
    dimensions = (255, 150, 4)
    with patch("image_otd.image_otd.Path.mkdir"):  # Mock directory creation
        result = process_image(sample_image, dimensions)

        assert isinstance(result, Path)
        processed_img = Image.open(sample_image)  # Verify original image still exists
        assert processed_img.size == (800, 600)  # Original dimensions


def test_process_image_file_not_found():
    invalid_path = Path("nonexistent.jpg")
    dimensions = (255, 150, 4)

    with pytest.raises(
        ImageProcessingError,
        match="Image processing failed: .*No such file or directory",
    ):
        process_image(invalid_path, dimensions)


def test_process_image_invalid_format(tmp_path):
    # Create an invalid image file
    invalid_image = tmp_path / "invalid.jpg"
    invalid_image.write_text("This is not an image")
    dimensions = (255, 150, 4)

    with pytest.raises(ImageProcessingError, match="Invalid or corrupt image file"):
        process_image(invalid_image, dimensions)


def test_process_image_processing_error(sample_image):
    dimensions = (-1, -1, -1)  # Invalid dimensions

    with pytest.raises(ImageProcessingError, match="Image processing failed"):
        process_image(sample_image, dimensions)


def test_upload_pic_otd_success():
    with patch("image_otd.image_otd.upload_file") as mock_upload, patch(
        "image_otd.image_otd.Path.exists", return_value=True
    ):

        mock_upload.return_value = ("http://example.com/image.jpg", None)
        result = upload_pic_otd()

        assert result == "http://example.com/image.jpg"
        mock_upload.assert_called_once()


def test_upload_pic_otd_file_not_found():
    with patch("image_otd.image_otd.Path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            upload_pic_otd()


def test_resize_full_cached():
    with patch("image_otd.image_otd.retrieve_from_json") as mock_retrieve:
        mock_retrieve.return_value = (True, ("url", "title", "link"))

        result = resize_full()
        assert result == ("url", "title", "link")


def test_resize_full_new_image(sample_image):
    with patch(
        "image_otd.image_otd.retrieve_from_json", return_value=(False, None)
    ), patch("image_otd.image_otd.get_flickr") as mock_get_flickr, patch(
        "image_otd.image_otd.process_image"
    ) as mock_process, patch(
        "image_otd.image_otd.upload_pic_otd"
    ) as mock_upload:

        # Setup mocks
        mock_get_flickr.return_value = FlickrImage(
            sample_image, "test_title", "test_link"
        )
        mock_process.return_value = Path("processed.jpg")
        mock_upload.return_value = "http://example.com/image.jpg"

        result = resize_full()

        assert result == ("http://example.com/image.jpg", "test_title", "test_link")
        mock_get_flickr.assert_called_once()
        mock_process.assert_called_once()
        mock_upload.assert_called_once()


def test_resize_full_flickr_error():
    with patch(
        "image_otd.image_otd.retrieve_from_json", return_value=(False, None)
    ), patch("image_otd.image_otd.get_flickr") as mock_get_flickr:

        mock_get_flickr.side_effect = FlickrAPIError("API Error")

        with pytest.raises(FlickrAPIError):
            resize_full()


def test_resize_full_processing_error(sample_image):
    with patch(
        "image_otd.image_otd.retrieve_from_json", return_value=(False, None)
    ), patch("image_otd.image_otd.get_flickr") as mock_get_flickr, patch(
        "image_otd.image_otd.process_image"
    ) as mock_process:

        mock_get_flickr.return_value = FlickrImage(
            sample_image, "test_title", "test_link"
        )
        mock_process.side_effect = ImageProcessingError("Processing failed")

        with pytest.raises(ImageProcessingError):
            resize_full()
