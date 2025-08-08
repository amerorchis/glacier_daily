from datetime import datetime
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

from sunrise_timelapse.vid_frame import (
    FileOperationError,
    TimelapseError,
    VideoProcessingError,
    find_frame,
    made_today,
    play_button,
    process_video,
)


@pytest.fixture
def mock_video():
    """Create a mock video with sample frames"""
    mock_cap = MagicMock()

    # Create three sample frames
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)  # Black frame
    frame2 = np.ones((100, 100, 3), dtype=np.uint8) * 255  # White frame
    frame3 = np.zeros((100, 100, 3), dtype=np.uint8)  # Red frame
    frame3[:, :, 2] = 255  # Set red channel to max

    mock_cap.read.side_effect = [
        (True, frame1),
        (True, frame2),
        (True, frame3),
        (False, None),
    ]

    return mock_cap


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample image file"""
    img_path = tmp_path / "sample_frame.jpg"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)
    return img_path


def test_find_frame_success(mock_video, tmp_path):
    """Test successful frame finding"""
    video_path = tmp_path / "test.mp4"
    # Create empty file
    video_path.touch()

    with (
        patch("cv2.VideoCapture", return_value=mock_video),
        patch("cv2.imwrite") as mock_imwrite,
        patch("sunrise_timelapse.vid_frame.play_button") as mock_play_button,
    ):

        result = find_frame(video_path)

        assert result is True
        mock_imwrite.assert_called_once()
        assert mock_video.read.call_count == 4  # 3 frames + EOF


def test_find_frame_no_file():
    """Test handling of missing video file"""
    with pytest.raises(VideoProcessingError):
        find_frame(Path("nonexistent.mp4"))


def test_find_frame_empty_video(tmp_path):
    """Test handling of empty video"""
    video_path = tmp_path / "empty.mp4"
    mock_cap = MagicMock()
    mock_cap.read.return_value = (False, None)

    with patch("cv2.VideoCapture", return_value=mock_cap):
        with pytest.raises(VideoProcessingError):
            find_frame(video_path)


def test_find_frame_cv2_error(mock_video, tmp_path):
    """Test handling of OpenCV errors"""
    video_path = tmp_path / "test.mp4"
    mock_video.read.side_effect = cv2.error("Test CV2 Error")

    with patch("cv2.VideoCapture", return_value=mock_video):
        with pytest.raises(VideoProcessingError):
            find_frame(video_path)


def test_play_button_missing_frame():
    """Test handling of missing frame image"""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileOperationError):
            play_button()


def test_play_button_missing_overlay():
    """Test handling of missing play button overlay"""
    with patch("PIL.Image.open") as mock_open:
        mock_open.side_effect = [MagicMock(), FileNotFoundError()]

        with pytest.raises(FileOperationError):
            play_button()


def test_made_today(tmp_path):
    """Test date verification of video file"""
    video_path = tmp_path / "test.mp4"
    video_path.touch()

    assert made_today(video_path) is True


def test_made_today_no_file():
    """Test handling of nonexistent file"""
    assert made_today(Path("nonexistent.mp4")) is False


@patch("sunrise_timelapse.vid_frame.retrieve_from_json")
def test_process_video_cached(mock_retrieve):
    """Test handling of cached video data"""
    mock_retrieve.return_value = (True, ("url", "frame"))

    result = process_video()
    assert result == ("url", "frame")


@patch("sunrise_timelapse.vid_frame.sunrise_timelapse_complete_time")
def test_process_video_too_early(mock_sunrise_time):
    """Test handling when it's too early for sunrise"""
    mock_sunrise_time.return_value = 3600  # 1 hour remaining

    result = process_video()
    assert result == ("", "")


@patch("sunrise_timelapse.vid_frame.retrieve_from_json", return_value=(False, None))
@patch("sunrise_timelapse.vid_frame.sunrise_timelapse_complete_time", return_value=0)
@patch("sunrise_timelapse.vid_frame.made_today", return_value=False)
def test_process_video_no_video(mock_made_today, mock_sunrise, mock_retrieve):
    """Test handling when no video is available"""
    result = process_video()
    assert result == (None, None)


@patch("sunrise_timelapse.vid_frame.sunrise_timelapse_complete_time", return_value=0)
@patch("sunrise_timelapse.vid_frame.made_today", return_value=True)
@patch("sunrise_timelapse.vid_frame.find_frame", return_value=True)
@patch("sunrise_timelapse.vid_frame.upload_file")
def test_process_video_success(mock_upload, mock_find, mock_made_today, mock_sunrise):
    """Test successful video processing"""
    mock_upload.side_effect = [("vid_url", None), ("frame_url", None)]

    result = process_video()
    assert result == ("vid_url", "frame_url")
    assert mock_upload.call_count == 2


@patch("sunrise_timelapse.vid_frame.sunrise_timelapse_complete_time", return_value=0)
@patch("sunrise_timelapse.vid_frame.made_today", return_value=True)
@patch("sunrise_timelapse.vid_frame.find_frame")
def test_process_video_frame_error(mock_find, mock_made_today, mock_sunrise):
    """Test handling of frame processing error"""
    mock_find.side_effect = VideoProcessingError("Test error")

    result = process_video()
    assert result == (None, None)
