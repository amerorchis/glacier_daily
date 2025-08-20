from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import gspread
import pytest

from notices.notices import get_notices


@pytest.fixture
def mock_gspread():
    with patch("gspread.authorize") as mock_auth:
        # Create mock client
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        # Setup the chain of calls
        mock_auth.return_value = mock_client
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_spreadsheet.sheet1 = mock_worksheet

        yield mock_worksheet


@pytest.fixture
def mock_credentials():
    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_file"
    ) as mock_creds:
        yield mock_creds


@pytest.fixture
def mock_env_vars():
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_APPLICATION_CREDENTIALS": "fake_credentials.json",
            "NOTICES_SPREADSHEET_ID": "fake_spreadsheet_id",
        },
    ):
        yield


def test_get_notices_with_current_notices(
    mock_gspread, mock_credentials, mock_env_vars
):
    # Setup current date for testing
    current_date = datetime.now()
    yesterday = (current_date - timedelta(days=1)).strftime("%m/%d/%Y")
    tomorrow = (current_date + timedelta(days=1)).strftime("%m/%d/%Y")

    # Mock worksheet data
    mock_data = [
        ["Start Date", "End Date", "Notice"],  # Header row
        [yesterday, tomorrow, "Test notice 1"],
        [yesterday, tomorrow, "Test notice 2"],
    ]
    mock_gspread.get_all_values.return_value = mock_data

    # Call function and verify result
    result = get_notices()
    expected = (
        '<ul style="margin:0 0 35px; padding-left:10px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">'
        + "<li>Test notice 1</li>\n<li>Test notice 2</li></ul>"
    )

    assert result == expected


def test_get_notices_with_no_current_notices(
    mock_gspread, mock_credentials, mock_env_vars
):
    # Setup dates outside current range
    past_start = (datetime.now() - timedelta(days=5)).strftime("%m/%d/%Y")
    past_end = (datetime.now() - timedelta(days=3)).strftime("%m/%d/%Y")

    mock_data = [
        ["Start Date", "End Date", "Notice"],
        [past_start, past_end, "Old notice"],
    ]
    mock_gspread.get_all_values.return_value = mock_data

    result = get_notices()
    expected = '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">There were no notices for today.</p>'

    assert result == expected


def test_get_notices_with_empty_sheet(mock_gspread, mock_credentials, mock_env_vars):
    # Mock empty worksheet
    mock_gspread.get_all_values.return_value = [["Start Date", "End Date", "Notice"]]

    result = get_notices()
    expected = '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">There were no notices for today.</p>'

    assert result == expected


def test_get_notices_with_invalid_data(mock_gspread, mock_credentials, mock_env_vars):
    # Mock invalid data format
    mock_data = [
        ["Start Date", "End Date", "Notice"],
        ["invalid_date", "invalid_date", "Test notice"],
    ]
    mock_gspread.get_all_values.return_value = mock_data

    result = get_notices()
    expected = '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">There were no notices for today.</p>'

    assert result == expected


def test_get_notices_api_error(mock_gspread, mock_credentials, mock_env_vars):
    # Create a mock Response object
    mock_response = Mock()
    mock_response.json.return_value = {
        "error": {"code": 429, "message": "Too Many Requests"}
    }

    # Mock API error with proper Response object
    mock_gspread.get_all_values.side_effect = gspread.exceptions.APIError(mock_response)

    expected = '<p style="margin:0 0 35px; font-size:12px; line-height:18px; color:#333333;">There was an error retrieving notices today.</p>'
    result = get_notices()
    assert result == expected


def test_get_notices_with_incomplete_data(
    mock_gspread, mock_credentials, mock_env_vars
):
    current_date = datetime.now()
    yesterday = (current_date - timedelta(days=1)).strftime("%m/%d/%Y")
    tomorrow = (current_date + timedelta(days=1)).strftime("%m/%d/%Y")

    # Mock data with missing fields
    mock_data = [
        ["Start Date", "End Date", "Notice"],
        [yesterday, tomorrow, ""],  # Missing notice
        [yesterday, "", "Test notice"],  # Missing end date
        ["", tomorrow, "Test notice"],  # Missing start date
        [yesterday, tomorrow, "Valid notice"],  # Valid entry
    ]
    mock_gspread.get_all_values.return_value = mock_data

    result = get_notices()
    expected = (
        '<ul style="margin:0 0 35px; padding-left:10px; padding-top:0px; font-size:12px; line-height:18px; color:#333333;">'
        + "<li>Valid notice</li></ul>"
    )

    assert result == expected
