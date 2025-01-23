import pytest
import json
from unittest.mock import patch, Mock, ANY
from datetime import datetime
from ftplib import FTP
import socket
import io
import os
import sys

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pragma: no cover

from sunrise_timelapse.timelapse_json import send_timelapse_data, gen_json

# Test data
SAMPLE_FILES = [
    "1_21_2025_sunrise_timelapse.mp4",
    "12_31_2024_sunrise_timelapse.mp4",
    "12_30_2024_sunrise_timelapse.mp4",
    ".",
    "..",
]

EXPECTED_JSON_DATA = [
    {"date": ANY},  # We'll check this separately due to datetime
    {
        "id": "1_21_2025_sunrise_timelapse",
        "vid_src": "/daily/sunrise_vid/1_21_2025_sunrise_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=1_21_2025_sunrise_timelapse",
        "title": "1-21 Sunrise Timelapse",
        "string": "1-21 Sunrise",
    },
    {
        "id": "12_31_2024_sunrise_timelapse",
        "vid_src": "/daily/sunrise_vid/12_31_2024_sunrise_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=12_31_2024_sunrise_timelapse",
        "title": "12-31 Sunrise Timelapse",
        "string": "12-31 Sunrise",
    },
    {
        "id": "12_30_2024_sunrise_timelapse",
        "vid_src": "/daily/sunrise_vid/12_30_2024_sunrise_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=12_30_2024_sunrise_timelapse",
        "title": "12-30 Sunrise Timelapse",
        "string": "12-30 Sunrise",
    },
]


def test_gen_json_basic():
    """Test basic JSON generation with valid input files"""
    result = json.loads(gen_json(SAMPLE_FILES.copy()))

    print(result[1])
    # Check length
    assert len(result) == 4

    # Check date format in first element
    assert datetime.strptime(result[0]["date"].split(".")[0], "%Y-%m-%d %H:%M:%S")

    # Remove date entry for comparison
    result.pop(0)
    expected = EXPECTED_JSON_DATA[1:]
    assert result == expected


def test_gen_json_empty_list():
    """Test JSON generation with empty file list (after removing . and ..)"""
    with pytest.raises(ValueError):
        gen_json([".", ".."])


def test_gen_json_invalid_filename():
    """Test JSON generation with invalid filename format"""
    invalid_files = [".", "..", "invalid_file.mp4"]
    with pytest.raises(IndexError):
        gen_json(invalid_files)


def test_gen_json_sorting():
    """Test that files are sorted correctly by date"""
    files = [
        "1_21_2025_sunrise_timelapse.mp4",
        "12_31_2024_sunrise_timelapse.mp4",
        "12_30_2024_sunrise_timelapse.mp4",
        ".",
        "..",
    ]
    result = json.loads(gen_json(files))
    # Remove date entry
    result.pop(0)

    # Check that dates are in descending order
    dates = [entry["id"] for entry in result]
    assert dates == [
        "1_21_2025_sunrise_timelapse",
        "12_31_2024_sunrise_timelapse",
        "12_30_2024_sunrise_timelapse",
    ]


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
