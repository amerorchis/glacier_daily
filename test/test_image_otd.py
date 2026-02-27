from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.error import URLError

import pytest
from PIL import Image

from image_otd.flickr import FlickrAPIError, FlickrImage, _best_image_url, get_flickr
from image_otd.image_otd import (
    ImageProcessingError,
    get_image_otd,
    prepare_pic_otd,
    process_image,
    resize_full,
    upload_pic_otd,
)


@pytest.fixture
def mock_env_vars(mock_required_settings):
    env_vars = {
        "FLICKR_KEY": "test_key",
        "FLICKR_SECRET": "test_secret",
        "GLACIERNPS_UID": "test_uid",
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
                    "id": "test_id",
                    "title": "test_title",
                }
            ],
        }
    }


@pytest.fixture
def mock_sizes_response():
    return {
        "sizes": {
            "size": [
                {
                    "label": "Large",
                    "width": "1024",
                    "height": "768",
                    "source": "https://live.staticflickr.com/test/test_id_abc_b.jpg",
                },
                {
                    "label": "Large 1600",
                    "width": "1600",
                    "height": "1200",
                    "source": "https://live.staticflickr.com/test/test_id_abc_h.jpg",
                },
            ]
        }
    }


class TestBestImageUrl:
    """Tests for _best_image_url size selection logic."""

    def test_picks_smallest_above_threshold(self):
        """Should pick the smallest size >= 1040px, not the largest."""
        mock_api = Mock()
        mock_api.photos.getSizes.return_value = {
            "sizes": {
                "size": [
                    {"width": "800", "source": "https://flickr.com/800.jpg"},
                    {"width": "1024", "source": "https://flickr.com/1024.jpg"},
                    {"width": "1600", "source": "https://flickr.com/1600.jpg"},
                    {"width": "1040", "source": "https://flickr.com/1040.jpg"},
                ]
            }
        }
        result = _best_image_url(mock_api, "123")
        assert result == "https://flickr.com/1040.jpg"

    def test_falls_back_to_largest_when_none_meet_threshold(self):
        """When no size >= 1040px, should pick the largest available."""
        mock_api = Mock()
        mock_api.photos.getSizes.return_value = {
            "sizes": {
                "size": [
                    {"width": "500", "source": "https://flickr.com/500.jpg"},
                    {"width": "800", "source": "https://flickr.com/800.jpg"},
                ]
            }
        }
        result = _best_image_url(mock_api, "123")
        assert result == "https://flickr.com/800.jpg"

    def test_exact_threshold_match(self):
        """A size exactly at 1040px should be picked."""
        mock_api = Mock()
        mock_api.photos.getSizes.return_value = {
            "sizes": {
                "size": [
                    {"width": "800", "source": "https://flickr.com/800.jpg"},
                    {"width": "1040", "source": "https://flickr.com/1040.jpg"},
                ]
            }
        }
        result = _best_image_url(mock_api, "123")
        assert result == "https://flickr.com/1040.jpg"


def test_get_flickr_success(mock_env_vars, mock_flickr_response, mock_sizes_response):
    with (
        patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI,
        patch("image_otd.flickr.urllib.request.urlopen") as mock_urlopen,
        patch("builtins.open", create=True) as mock_open,
    ):
        # Setup mock FlickrAPI
        mock_api = Mock()
        mock_api.photos.search.return_value = mock_flickr_response
        mock_api.photos.getSizes.return_value = mock_sizes_response
        MockFlickrAPI.return_value = mock_api

        # Setup mock urlopen
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"fake image data"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Setup mock open
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = get_flickr()

        assert isinstance(result, FlickrImage)
        assert result.title == "test_title"
        assert result.link == "https://flickr.com/photos/glaciernps/test_id"
        assert isinstance(result.path, Path)


def test_get_flickr_missing_env_var(mock_required_settings):
    # Flickr vars are "" from conftest seeding — FlickrAPI will fail with empty creds
    with (
        patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI,
        pytest.raises(FlickrAPIError),
    ):
        MockFlickrAPI.return_value.photos.search.side_effect = Exception(
            "Invalid API Key"
        )
        get_flickr()


def test_get_flickr_api_error(mock_env_vars):
    with patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI:
        mock_api = Mock()
        mock_api.photos.search.side_effect = Exception("API Error")
        MockFlickrAPI.return_value = mock_api

        with pytest.raises(FlickrAPIError, match="Flickr API error"):
            get_flickr()


def test_get_flickr_download_error(
    mock_env_vars, mock_flickr_response, mock_sizes_response
):
    with (
        patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI,
        patch("image_otd.flickr.urllib.request.urlopen") as mock_urlopen,
        patch("builtins.open", create=True),
    ):
        mock_api = Mock()
        mock_api.photos.search.return_value = mock_flickr_response
        mock_api.photos.getSizes.return_value = mock_sizes_response
        MockFlickrAPI.return_value = mock_api

        mock_urlopen.side_effect = URLError("Download failed")

        with pytest.raises(FlickrAPIError, match="Failed to download image"):
            get_flickr()


@pytest.fixture
def sample_image(tmp_path):
    # Create a test image
    img_path = tmp_path / "test.jpg"
    image = Image.new("RGB", (800, 600), color="white")
    image.save(img_path)
    return img_path


def test_process_image_success(sample_image, tmp_path):
    with patch("image_otd.image_otd.Path.mkdir"):  # Mock directory creation
        result = process_image(sample_image)

        assert isinstance(result, Path)
        processed_img = Image.open(sample_image)  # Verify original image still exists
        assert processed_img.size == (800, 600)  # Original dimensions


def test_process_image_file_not_found():
    invalid_path = Path("nonexistent.jpg")

    with pytest.raises(
        ImageProcessingError,
        match="Image processing failed: .*No such file or directory",
    ):
        process_image(invalid_path)


def test_process_image_invalid_format(tmp_path):
    # Create an invalid image file
    invalid_image = tmp_path / "invalid.jpg"
    invalid_image.write_text("This is not an image")

    with pytest.raises(ImageProcessingError, match="Invalid or corrupt image file"):
        process_image(invalid_image)


def test_upload_pic_otd_success():
    mock_ftp = MagicMock()
    mock_ftp.__enter__ = MagicMock(return_value=mock_ftp)
    mock_ftp.__exit__ = MagicMock(return_value=False)
    mock_ftp.upload.return_value = ("http://example.com/image.jpg", None)

    with (
        patch("image_otd.image_otd.FTPSession", return_value=mock_ftp),
        patch("image_otd.image_otd.Path.exists", return_value=True),
    ):
        result = upload_pic_otd()

        assert result == "http://example.com/image.jpg"
        mock_ftp.upload.assert_called_once()


def test_upload_pic_otd_file_not_found():
    with (
        patch("image_otd.image_otd.Path.exists", return_value=False),
        pytest.raises(FileNotFoundError),
    ):
        upload_pic_otd()


def test_prepare_pic_otd():
    """Test prepare_pic_otd returns correct tuple."""
    with patch("image_otd.image_otd.Path.exists", return_value=True):
        directory, filename, local_path = prepare_pic_otd()
        assert directory == "picture"
        assert filename.endswith("_pic_otd.jpg")
        assert "resized_image_otd.jpg" in local_path


def test_resize_full_skip_upload(sample_image):
    """Test resize_full with skip_upload=True returns None for URL."""
    with (
        patch("image_otd.image_otd.get_flickr") as mock_get_flickr,
        patch("image_otd.image_otd.process_image"),
    ):
        mock_get_flickr.return_value = FlickrImage(
            sample_image, "test_title", "test_link"
        )
        result = resize_full(skip_upload=True)
        assert result == (None, "test_title", "test_link")


def test_resize_full_new_image(sample_image):
    with (
        patch("image_otd.image_otd.get_flickr") as mock_get_flickr,
        patch("image_otd.image_otd.process_image") as mock_process,
        patch("image_otd.image_otd.upload_pic_otd") as mock_upload,
    ):
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
    with patch("image_otd.image_otd.get_flickr") as mock_get_flickr:
        mock_get_flickr.side_effect = FlickrAPIError("API Error")

        with pytest.raises(FlickrAPIError):
            resize_full()


def test_resize_full_processing_error(sample_image):
    with (
        patch("image_otd.image_otd.get_flickr") as mock_get_flickr,
        patch("image_otd.image_otd.process_image") as mock_process,
    ):
        mock_get_flickr.return_value = FlickrImage(
            sample_image, "test_title", "test_link"
        )
        mock_process.side_effect = ImageProcessingError("Processing failed")

        with pytest.raises(ImageProcessingError):
            resize_full()


def test_get_image_otd_success():
    """Test get_image_otd wrapper returns resize_full result on success."""
    with patch("image_otd.image_otd.resize_full") as mock_resize:
        mock_resize.return_value = (
            "http://example.com/img.jpg",
            "Title",
            "http://link",
        )
        result = get_image_otd()
        assert result == ("http://example.com/img.jpg", "Title", "http://link")


def test_get_image_otd_flickr_error_fallback():
    """Test get_image_otd returns fallback on FlickrAPIError."""
    with patch("image_otd.image_otd.resize_full") as mock_resize:
        mock_resize.side_effect = FlickrAPIError("API down")
        result = get_image_otd()
        assert result == ("", "", "")


def test_get_flickr_url_error_429_retry(
    mock_env_vars, mock_flickr_response, mock_sizes_response
):
    """Test that 429 URLError triggers backoff and raises after retries exhausted."""
    with (
        patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI,
        patch("image_otd.flickr.urllib.request.urlopen") as mock_urlopen,
        patch("image_otd.flickr.time.sleep") as mock_sleep,
    ):
        mock_api = Mock()
        mock_api.photos.search.return_value = mock_flickr_response
        mock_api.photos.getSizes.return_value = mock_sizes_response
        MockFlickrAPI.return_value = mock_api

        # Both attempts raise 429 URLError - exhausts retries
        error_429_a = URLError("Too Many Requests")
        error_429_a.code = 429
        error_429_b = URLError("Too Many Requests")
        error_429_b.code = 429

        mock_urlopen.side_effect = [error_429_a, error_429_b]

        with pytest.raises(FlickrAPIError, match="Too many requests"):
            get_flickr()
        assert mock_sleep.call_count == 1


def test_get_flickr_no_photos_found(mock_env_vars, mock_sizes_response):
    """Test retry loop when initial search returns no photos."""
    with (
        patch("image_otd.flickr.FlickrAPI") as MockFlickrAPI,
        patch("image_otd.flickr.urllib.request.urlopen") as mock_urlopen,
        patch("builtins.open", create=True) as mock_open,
    ):
        mock_api = Mock()
        # First total query, then empty result, then result with photo
        empty_response = {"photos": {"total": "100", "photo": []}}
        valid_response = {
            "photos": {
                "total": "100",
                "photo": [
                    {
                        "id": "123",
                        "title": "Found",
                    }
                ],
            }
        }
        mock_api.photos.search.side_effect = [
            {"photos": {"total": "100", "photo": []}},  # per_page=1 total query
            empty_response,  # first random page - empty
            valid_response,  # retry - found
        ]
        mock_api.photos.getSizes.return_value = mock_sizes_response
        MockFlickrAPI.return_value = mock_api

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"data"
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        mock_file = Mock()
        mock_open.return_value.__enter__ = Mock(return_value=mock_file)
        mock_open.return_value.__exit__ = Mock(return_value=False)

        result = get_flickr()
        assert result.title == "Found"
