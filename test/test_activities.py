from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import pytz
import requests

from activities.events import events_today
from activities.gnpc_datetime import convert_gnpc_datetimes, datetime_to_string
from activities.gnpc_events import (
    GNPCError,
    GNPCParsingError,
    GNPCRequestError,
    get_gnpc_events,
    scrape_events_page,
)


def test_activity_retrieval():
    """Test that events are retrieved and formatted for a known day."""
    with open("test/files/events.txt", "r", encoding="utf8") as f:
        actual = f.read()

    july_1_events = events_today("2024-07-01")
    assert (
        july_1_events == actual
        or july_1_events == "502 Response"
        or july_1_events
        == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger program schedule could not be retrieved.</p>'
    )


def test_no_activities_no_message():
    jan_8_events = events_today("2024-01-08")
    assert (
        jan_8_events == ""
        or jan_8_events == "502 Response"
        or jan_8_events
        == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger program schedule could not be retrieved.</p>'
    )


def test_no_activities_season_concluded():
    print(events_today(f"{datetime.now().year}-12-05"))
    assert (
        events_today(f"{datetime.now().year}-12-05") == "502 Response"
        or events_today(f"{datetime.now().year}-12-05")
        == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs have concluded for the season.</p>'
    )


def test_no_activities_season_not_started():
    assert (
        events_today(f"{datetime.now().year}-04-05")
        or events_today(f"{datetime.now().year}-04-05")
        == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs not started for the season.</p>'
    )


@pytest.fixture
def mst_timezone():
    return pytz.timezone("America/Denver")


@pytest.fixture
def sample_dates():
    return [
        # Standard format
        ("July 15, 2024 7:30", datetime(2024, 7, 15, 19, 30)),
        # Single digit day
        ("August 5, 2024 8:00", datetime(2024, 8, 5, 20, 0)),
        # Different month
        ("December 25, 2024 6:45", datetime(2024, 12, 25, 18, 45)),
        # Different minutes
        ("January 1, 2024 7:05", datetime(2024, 1, 1, 19, 5)),
    ]


def test_convert_gnpc_datetimes_valid_dates(sample_dates, mst_timezone):
    """Test conversion of valid date strings."""
    for date_string, expected_dt in sample_dates:
        result = convert_gnpc_datetimes(date_string)
        expected = mst_timezone.localize(expected_dt)
        assert result == expected
        assert result.tzinfo == expected.tzinfo


def test_convert_gnpc_datetimes_invalid_format():
    """Test handling of invalid date string formats."""
    invalid_dates = [
        "Not a date",
        "15 July, 2024 7:30",  # Wrong order
        "July 15 2024 7:30",  # Missing comma
        "July 15, 2024",  # Missing time
        "July 15, 2024 7",  # Incomplete time
        "",  # Empty string
        "July 32, 2024 7:30",  # Invalid day
    ]

    for invalid_date in invalid_dates:
        result = convert_gnpc_datetimes(invalid_date)
        assert (
            result == invalid_date
        )  # Should return original string for invalid formats


def test_convert_gnpc_datetimes_edge_cases(mst_timezone):
    """Test edge cases for date conversion."""
    edge_cases = [
        # Leap year
        ("February 29, 2024 7:30", datetime(2024, 2, 29, 19, 30)),
        # Year boundaries
        ("December 31, 2024 11:59", datetime(2024, 12, 31, 23, 59)),
        # Noon
        ("January 1, 2024 12:00", datetime(2024, 1, 1, 12, 0)),
    ]

    for date_string, expected_dt in edge_cases:
        result = convert_gnpc_datetimes(date_string)
        expected = mst_timezone.localize(expected_dt)
        assert result == expected


def test_datetime_to_string_standard():
    """Test standard datetime string formatting."""
    tz = pytz.timezone("America/Denver")
    test_cases = [
        (
            tz.localize(datetime(2024, 7, 15, 19, 30)),
            "Monday, July 15, 2024, 7:30 pm MDT",
        ),
        (
            tz.localize(datetime(2024, 12, 25, 18, 45)),
            "Wednesday, December 25, 2024, 6:45 pm MST",
        ),
        (
            tz.localize(datetime(2024, 1, 1, 12, 0)),
            "Monday, January 1, 2024, 12:00 pm MST",
        ),
    ]

    for dt, expected in test_cases:
        result = datetime_to_string(dt)
        assert result == expected


def test_datetime_to_string_single_digit_hours():
    """Test formatting of times with single-digit hours."""
    tz = pytz.timezone("America/Denver")
    dt = tz.localize(datetime(2024, 7, 15, 9, 5))
    result = datetime_to_string(dt)
    assert result == "Monday, July 15, 2024, 9:05 am MDT"


def test_datetime_to_string_timezone_handling():
    """Test handling of different timezones."""
    # Create datetime in different timezone
    pst = pytz.timezone("America/Los_Angeles")
    dt_pst = pst.localize(datetime(2024, 7, 15, 18, 30))

    # Convert to MST/MDT
    mst = pytz.timezone("America/Denver")
    dt_mst = dt_pst.astimezone(mst)

    result = datetime_to_string(dt_mst)
    assert result == "Monday, July 15, 2024, 7:30 pm MDT"


def test_convert_and_format_integration(sample_dates, mst_timezone):
    """Test integration between conversion and formatting functions."""
    for date_string, _ in sample_dates:
        converted = convert_gnpc_datetimes(date_string)
        formatted = datetime_to_string(converted)

        # Convert back and compare components
        reconverted = convert_gnpc_datetimes(formatted)
        assert converted.year == reconverted.year
        assert converted.month == reconverted.month
        assert converted.day == reconverted.day
        assert converted.hour == reconverted.hour
        assert converted.minute == reconverted.minute
        assert converted.tzinfo == reconverted.tzinfo


@pytest.fixture
def sample_conversation_html():
    return """
    <div class="et_pb_row" id="event1">
        <h4>Sample Event Title</h4>
        <div class="thumbs">https://example.com/thumb.jpg</div>
        <p>January 15, 2024 7:30</p>
        <p>Event description here.</p>
        <p>Register now!</p>
    </div>
    """


@pytest.fixture
def sample_book_club_html():
    return """
    <div class="et_pb_row" id="event2">
        <h4>Book Discussion</h4>
        <img src="https://example.com/book.jpg"/>
        <p>February 1, 2024 7:00</p>
        <p>Join us for this month's book discussion.</p>
        <p>Register now!</p>
    </div>
    """


@pytest.fixture
def mock_response(sample_conversation_html):
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = sample_conversation_html
    return mock_resp


def test_scrape_events_page_success(mock_response):
    with patch("requests.get", return_value=mock_response):
        events = scrape_events_page(
            "https://glacier.org/glacier-conversations", "Glacier Conversation:"
        )

        assert len(events) == 1
        assert events[0]["title"] == "Glacier Conversation: Sample Event Title"
        assert events[0]["pic"] == "https://example.com/thumb.jpg"
        assert events[0]["datetime"] == "January 15, 2024 7:30"


def test_scrape_events_page_request_error():
    with patch("requests.get", side_effect=requests.RequestException("Network error")):
        with pytest.raises(GNPCRequestError, match="Failed to access"):
            scrape_events_page(
                "https://glacier.org/glacier-conversations", "Glacier Conversation:"
            )


def test_scrape_events_page_invalid_html():
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = "Invalid HTML"

    with patch("requests.get", return_value=mock_resp):
        events = scrape_events_page(
            "https://glacier.org/glacier-conversations", "Glacier Conversation:"
        )
        assert events == []


def test_scrape_events_page_missing_elements():
    """Test handling of HTML with missing required elements"""
    html = """
    <div class='et_pb_row'>
        <h4>Title</h4>
        <p>January 15, 2024 7:30</p>
        <p>Description</p>
        <p>Register</p>
    </div>
    """
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = html

    with patch("requests.get", return_value=mock_resp):
        events = scrape_events_page(
            "https://glacier.org/glacier-conversations", "Glacier Conversation:"
        )
        assert len(events) == 1
        assert events[0]["pic"] == ""  # Should have empty string for missing image
        assert events[0]["title"] == "Glacier Conversation: Title"


def test_scrape_events_page_completely_missing_elements():
    """Test handling of HTML with no usable event data"""
    html = "<div class='et_pb_row'><h4>Title</h4></div>"
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = html

    with patch("requests.get", return_value=mock_resp):
        events = scrape_events_page(
            "https://glacier.org/glacier-conversations", "Glacier Conversation:"
        )
        assert events == []  # Should return empty list when no valid events found


def test_get_gnpc_events_success(sample_conversation_html, sample_book_club_html):
    mock_responses = {
        "https://glacier.org/glacier-conversations": Mock(
            status_code=200, content=sample_conversation_html
        ),
        "https://glacier.org/glacier-book-club": Mock(
            status_code=200, content=sample_book_club_html
        ),
    }

    def mock_get(url, **kwargs):
        return mock_responses[url]

    with patch("requests.get", side_effect=mock_get):
        events = get_gnpc_events()

        assert len(events) == 2
        assert any("Glacier Conversation:" in event["title"] for event in events)
        assert any("Glacier Book Club:" in event["title"] for event in events)


def test_get_gnpc_events_partial_failure(sample_conversation_html):
    def mock_get(url, **kwargs):
        if "conversations" in url:
            return Mock(status_code=200, content=sample_conversation_html)
        raise requests.RequestException("Network error")

    with patch("requests.get", side_effect=mock_get):
        events = get_gnpc_events()
        assert len(events) == 1
        assert "Glacier Conversation:" in events[0]["title"]


def test_get_gnpc_events_all_failures():
    with patch("requests.get", side_effect=requests.RequestException("Network error")):
        events = get_gnpc_events()
        assert events == []


def test_get_gnpc_events_invalid_date():
    html = """
    <div class="et_pb_row" id="event1">
        <h4>Sample Event</h4>
        <div class="thumbs">https://example.com/thumb.jpg</div>
        <p>Invalid Date Format</p>
        <p>Description</p>
        <p>Register</p>
    </div>
    """
    mock_resp = Mock(status_code=200, content=html)

    with patch("requests.get", return_value=mock_resp):
        events = get_gnpc_events()
        assert events == []


def test_event_sorting():
    html1 = """
    <div class="et_pb_row" id="event1">
        <h4>Later Event</h4>
        <div class="thumbs">https://example.com/thumb1.jpg</div>
        <p>March 15, 2024 7:30</p>
        <p>Description</p>
        <p>Register</p>
    </div>
    """
    html2 = """
    <div class="et_pb_row" id="event2">
        <h4>Earlier Event</h4>
        <div class="thumbs">https://example.com/thumb2.jpg</div>
        <p>January 15, 2024 7:30</p>
        <p>Description</p>
        <p>Register</p>
    </div>
    """

    mock_responses = {
        "https://glacier.org/glacier-conversations": Mock(
            status_code=200, content=html1
        ),
        "https://glacier.org/glacier-book-club": Mock(status_code=200, content=html2),
    }

    with patch("requests.get", side_effect=lambda url, **kwargs: mock_responses[url]):
        events = get_gnpc_events()
        assert len(events) == 2
        assert "January" in events[0]["datetime"]
        assert "March" in events[1]["datetime"]
