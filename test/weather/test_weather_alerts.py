import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from shared.data_types import AlertBullet
from weather.weather_alerts import WeatherAlert, WeatherAlertService, weather_alerts


@pytest.fixture
def weather_service():
    return WeatherAlertService()


@pytest.fixture
def sample_alert():
    return WeatherAlert(
        headline="High Wind Watch",
        description="* WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front.",
        issued_time=datetime(2025, 1, 13, 13, 13),
        full_text="High Wind Watch issued January 13 at 1:13PM MST: * WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front.",
    )


@pytest.fixture
def sample_api_response():
    return {
        "features": [
            {
                "properties": {
                    "headline": "High Wind Watch issued January 13 at 1:13PM MST",
                    "description": "* WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front.",
                    "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ301"],
                    "severity": "Severe",
                    "status": "Actual",
                    "messageType": "Alert",
                    "event": "High Wind Watch",
                    "sent": "2025-01-13T13:13:00-07:00",
                }
            },
            {
                "properties": {
                    "headline": "Winter Storm Warning issued January 13 at 2:13PM MST",
                    "description": "* WHAT...Heavy snow expected.\n\n* WHERE...Northern Rocky Mountains.",
                    "affectedZones": [
                        "https://api.weather.gov/zones/forecast/MTZ999"
                    ],  # Non-local zone
                    "severity": "Severe",
                    "status": "Actual",
                    "messageType": "Alert",
                    "event": "Winter Storm Warning",
                    "sent": "2025-01-13T14:13:00-07:00",
                }
            },
        ]
    }


class TestWeatherAlertService:
    def test_parse_alert_time(self, weather_service):
        text = "High Wind Watch issued January 13 at 1:13PM MST"
        result = weather_service.parse_alert_time(text)
        assert isinstance(result, datetime)
        assert result.hour == 13
        assert result.minute == 13
        assert result.day == 13

    def test_parse_alert_time_invalid(self, weather_service):
        text = "Invalid alert text"
        result = weather_service.parse_alert_time(text)
        assert result is None

    def test_parse_nested_bullets(self, weather_service):
        text = "Alert Title: * WHAT...Test alert.\n\n* WHERE...Test location."
        headline, bullets = weather_service.parse_nested_bullets(text)
        assert headline == "Alert Title"
        assert len(bullets) == 2
        assert bullets[0] == "What: Test alert."
        assert bullets[1] == "Where: Test location."

    def test_parse_nested_bullets_no_bullets(self, weather_service):
        text = "Alert Title: Simple alert with no bullets"
        headline, bullets = weather_service.parse_nested_bullets(text)
        assert headline == "Alert Title"
        assert len(bullets) == 0

    def test_format_html_message_single_alert(self, weather_service, sample_alert):
        result = weather_service.format_html_message([sample_alert])
        assert "Alert from" in result  # No 's' in "Alert" for single alert
        assert "<ul" in result
        assert "What: " in result
        assert "Where: " in result

    def test_format_html_message_multiple_alerts(self, weather_service, sample_alert):
        alerts = [sample_alert, sample_alert]
        result = weather_service.format_html_message(alerts)
        assert "Alerts from" in result  # Plural "Alerts" for multiple
        assert result.count("<ul") > len(alerts)  # Main list plus nested lists

    def test_format_html_message_empty(self, weather_service):
        result = weather_service.format_html_message([])
        assert result == ""

    @patch("requests.get")
    def test_fetch_alerts_success(self, mock_get, weather_service, sample_api_response):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(sample_api_response)
        mock_get.return_value = mock_response

        result = weather_service.fetch_alerts()
        assert len(result) == 2
        assert "High Wind Watch" in result[0]["properties"]["headline"]

    @patch("weather.weather_alerts.sleep")
    @patch("requests.get")
    def test_fetch_alerts_retry_then_success(
        self, mock_get, _mock_sleep, weather_service, sample_api_response
    ):
        fail_response = Mock()
        fail_response.status_code = 500

        success_response = Mock()
        success_response.status_code = 200
        success_response.content = json.dumps(sample_api_response)

        mock_get.side_effect = [fail_response, success_response]

        result = weather_service.fetch_alerts()
        assert len(result) == 2
        assert mock_get.call_count == 2

    def test_filter_local_alerts(self, weather_service, sample_api_response):
        alerts = sample_api_response["features"]
        result = weather_service.filter_local_alerts(alerts)
        assert len(result) == 1
        assert "High Wind Watch" in result[0]["headline"]

    # --- filter_by_relevance tests ---

    def test_filter_by_relevance_keeps_severe_and_extreme(self, weather_service):
        alerts = [
            {"severity": "Extreme", "status": "Actual", "messageType": "Alert"},
            {"severity": "Severe", "status": "Actual", "messageType": "Alert"},
            {"severity": "Moderate", "status": "Actual", "messageType": "Alert"},
            {"severity": "Minor", "status": "Actual", "messageType": "Alert"},
            {"severity": "Unknown", "status": "Actual", "messageType": "Alert"},
        ]
        result = weather_service.filter_by_relevance(alerts)
        assert len(result) == 2
        assert all(a["severity"] in ("Extreme", "Severe") for a in result)

    def test_filter_by_relevance_excludes_non_actual(self, weather_service):
        alerts = [
            {"severity": "Severe", "status": "Test", "messageType": "Alert"},
            {"severity": "Severe", "status": "Exercise", "messageType": "Alert"},
            {"severity": "Severe", "status": "Draft", "messageType": "Alert"},
            {"severity": "Severe", "status": "Actual", "messageType": "Alert"},
        ]
        result = weather_service.filter_by_relevance(alerts)
        assert len(result) == 1
        assert result[0]["status"] == "Actual"

    def test_filter_by_relevance_excludes_cancellations(self, weather_service):
        alerts = [
            {"severity": "Severe", "status": "Actual", "messageType": "Cancel"},
            {"severity": "Severe", "status": "Actual", "messageType": "Alert"},
            {"severity": "Severe", "status": "Actual", "messageType": "Update"},
        ]
        result = weather_service.filter_by_relevance(alerts)
        assert len(result) == 2
        assert all(a["messageType"] != "Cancel" for a in result)

    def test_filter_by_relevance_empty_input(self, weather_service):
        assert weather_service.filter_by_relevance([]) == []

    # --- deduplicate_alerts tests ---

    def test_deduplicate_by_event_field(self, weather_service):
        alerts = [
            {
                "event": "High Wind Watch",
                "sent": "2025-01-13T13:00:00-07:00",
                "headline": "older",
            },
            {
                "event": "High Wind Watch",
                "sent": "2025-01-13T15:00:00-07:00",
                "headline": "newer",
            },
            {
                "event": "Winter Storm Warning",
                "sent": "2025-01-13T14:00:00-07:00",
                "headline": "storm",
            },
        ]
        result = weather_service.deduplicate_alerts(alerts)
        assert len(result) == 2
        events = {a["event"] for a in result}
        assert events == {"High Wind Watch", "Winter Storm Warning"}
        hw = next(a for a in result if a["event"] == "High Wind Watch")
        assert hw["headline"] == "newer"

    def test_deduplicate_no_duplicates(self, weather_service):
        alerts = [
            {"event": "High Wind Watch", "sent": "2025-01-13T13:00:00-07:00"},
            {"event": "Winter Storm Warning", "sent": "2025-01-13T14:00:00-07:00"},
        ]
        result = weather_service.deduplicate_alerts(alerts)
        assert len(result) == 2

    def test_deduplicate_empty(self, weather_service):
        assert weather_service.deduplicate_alerts([]) == []

    # --- sort_alerts tests ---

    def test_sort_by_severity_then_time(self, weather_service):
        alerts = [
            {"severity": "Severe", "sent": "2025-01-13T15:00:00-07:00"},
            {"severity": "Extreme", "sent": "2025-01-13T13:00:00-07:00"},
            {"severity": "Severe", "sent": "2025-01-13T16:00:00-07:00"},
            {"severity": "Extreme", "sent": "2025-01-13T14:00:00-07:00"},
        ]
        result = weather_service.sort_alerts(alerts)
        assert result[0]["severity"] == "Extreme"
        assert result[0]["sent"] == "2025-01-13T14:00:00-07:00"
        assert result[1]["severity"] == "Extreme"
        assert result[1]["sent"] == "2025-01-13T13:00:00-07:00"
        assert result[2]["severity"] == "Severe"
        assert result[2]["sent"] == "2025-01-13T16:00:00-07:00"
        assert result[3]["severity"] == "Severe"
        assert result[3]["sent"] == "2025-01-13T15:00:00-07:00"

    def test_sort_empty(self, weather_service):
        assert weather_service.sort_alerts([]) == []

    # --- process_alerts tests ---

    def test_process_alerts(self, weather_service):
        alerts = [
            {
                "headline": "High Wind Watch issued January 13 at 1:13PM MST",
                "description": "* WHAT...Test alert",
                "severity": "Severe",
                "status": "Actual",
                "messageType": "Alert",
                "event": "High Wind Watch",
                "sent": "2025-01-13T13:13:00-07:00",
            }
        ]
        result = weather_service.process_alerts(alerts)
        assert len(result) == 1
        assert isinstance(result[0], WeatherAlert)
        assert "High Wind Watch" in result[0].headline

    def test_process_alerts_deduplication(self, weather_service):
        alerts = [
            {
                "headline": "High Wind Watch issued January 13 at 1:13PM MST",
                "description": "* WHAT...Test 1",
                "severity": "Severe",
                "status": "Actual",
                "messageType": "Alert",
                "event": "High Wind Watch",
                "sent": "2025-01-13T13:13:00-07:00",
            },
            {
                "headline": "High Wind Watch issued January 13 at 2:13PM MST",
                "description": "* WHAT...Test 2",
                "severity": "Severe",
                "status": "Actual",
                "messageType": "Alert",
                "event": "High Wind Watch",
                "sent": "2025-01-13T14:13:00-07:00",
            },
        ]
        result = weather_service.process_alerts(alerts)
        assert len(result) == 1
        assert "Test 2" in result[0].description

    def test_full_pipeline_filters_dedupes_and_sorts(self, weather_service):
        """End-to-end: relevance filter + dedup + sort."""
        alerts = [
            {
                "severity": "Extreme",
                "status": "Actual",
                "messageType": "Alert",
                "event": "Blizzard Warning",
                "sent": "2025-01-13T10:00:00-07:00",
                "headline": "Blizzard Warning issued January 13 at 10:00AM MST",
                "description": "* WHAT...Blizzard conditions.",
            },
            {
                "severity": "Severe",
                "status": "Actual",
                "messageType": "Alert",
                "event": "High Wind Watch",
                "sent": "2025-01-13T14:00:00-07:00",
                "headline": "High Wind Watch issued January 13 at 2:00PM MST",
                "description": "* WHAT...Wind.",
            },
            {
                "severity": "Moderate",
                "status": "Actual",
                "messageType": "Alert",
                "event": "Wind Advisory",
                "sent": "2025-01-13T12:00:00-07:00",
                "headline": "Wind Advisory issued January 13 at 12:00PM MST",
                "description": "* WHAT...Light wind.",
            },
            {
                "severity": "Severe",
                "status": "Actual",
                "messageType": "Cancel",
                "event": "Winter Storm Warning",
                "sent": "2025-01-13T15:00:00-07:00",
                "headline": "Winter Storm Warning issued January 13 at 3:00PM MST",
                "description": "Cancelled.",
            },
            {
                "severity": "Extreme",
                "status": "Test",
                "messageType": "Alert",
                "event": "Tornado Warning",
                "sent": "2025-01-13T16:00:00-07:00",
                "headline": "Tornado Warning issued January 13 at 4:00PM MST",
                "description": "Test only.",
            },
        ]
        result = weather_service.process_alerts(alerts)
        assert len(result) == 2
        assert "Blizzard" in result[0].headline
        assert "High Wind" in result[1].headline


class TestMainFunction:
    @patch.object(WeatherAlertService, "fetch_alerts")
    def test_weather_alerts_success(self, mock_fetch, sample_api_response):
        mock_fetch.return_value = sample_api_response["features"]
        result = weather_alerts()
        assert isinstance(result, list)
        assert len(result) == 1  # One local + severe + actual alert
        assert isinstance(result[0], AlertBullet)
        assert result[0].headline

    @patch.object(WeatherAlertService, "fetch_alerts")
    def test_weather_alerts_no_alerts(self, mock_fetch):
        mock_fetch.return_value = []
        result = weather_alerts()
        assert result == []

    @patch.object(WeatherAlertService, "fetch_alerts")
    def test_weather_alerts_error_handling(self, mock_fetch):
        mock_fetch.side_effect = Exception("Test error")
        result = weather_alerts()
        assert result == []
