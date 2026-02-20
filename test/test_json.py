import base64
import json
from unittest.mock import mock_open, patch

import pytest

from shared.retrieve_from_json import retrieve_from_json


class MockDateTime:
    @staticmethod
    def strftime(format_string):
        return "2025-01-22"


class MockDateTimeNow:
    @staticmethod
    def now():
        return MockDateTime()


@pytest.fixture
def sample_json_data():
    return {
        "date": "2025-01-22",
        "weather1": base64.b64encode(b"Test weather data").decode(),
        "peak": base64.b64encode(b"Test peak data").decode(),
        "roads": base64.b64encode(b"Test road data").decode(),
    }


def test_successful_retrieval(sample_json_data):
    mock_file = mock_open(read_data=json.dumps(sample_json_data))

    with (
        patch("builtins.open", mock_file),
        patch("shared.retrieve_from_json.now_mountain", return_value=MockDateTime()),
    ):
        success, values = retrieve_from_json(["weather1", "peak", "roads"])

        assert success is True
        assert values == ["Test weather data", "Test peak data", "Test road data"]


def test_date_mismatch(sample_json_data):
    mock_file = mock_open(read_data=json.dumps(sample_json_data))

    with patch("builtins.open", mock_file), patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "2025-01-23"

        success, values = retrieve_from_json(["weather1"])

        assert success is False
        assert values is None


def test_missing_keys(sample_json_data):
    mock_file = mock_open(read_data=json.dumps(sample_json_data))

    with patch("builtins.open", mock_file), patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "2025-01-22"

        success, values = retrieve_from_json(["nonexistent_key"])

        assert success is False
        assert values is None


def test_file_not_found():
    with patch("builtins.open", mock_open()) as mock_file:
        mock_file.side_effect = FileNotFoundError

        success, values = retrieve_from_json(["weather1"])

        assert success is False
        assert values is None


def test_invalid_json():
    mock_file = mock_open(read_data="invalid json")

    with patch("builtins.open", mock_file):
        success, values = retrieve_from_json(["weather1"])

        assert success is False
        assert values is None


def test_empty_value_handling(sample_json_data):
    sample_json_data["weather1"] = ""
    mock_file = mock_open(read_data=json.dumps(sample_json_data))

    with patch("builtins.open", mock_file), patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "2025-01-22"

        success, values = retrieve_from_json(["weather1"])

        assert success is False
        assert values is None


def test_invalid_base64():
    data = {"date": "2025-01-22", "weather1": "invalid base64!"}
    mock_file = mock_open(read_data=json.dumps(data))

    with patch("builtins.open", mock_file), patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "2025-01-22"

        success, values = retrieve_from_json(["weather1"])

        assert success is False
        assert values is None
