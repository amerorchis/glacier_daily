import sys
import os
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import json

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from weather.weather_alerts import WeatherAlertService, WeatherAlert, weather_alerts

@pytest.fixture
def weather_service():
    return WeatherAlertService()

@pytest.fixture
def sample_alert():
    return WeatherAlert(
        headline="High Wind Watch",
        description="* WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front.",
        issued_time=datetime(2025, 1, 13, 13, 13),
        full_text="High Wind Watch issued January 13 at 1:13PM MST: * WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front."
    )

@pytest.fixture
def sample_api_response():
    return {
        "features": [
            {
                "properties": {
                    "headline": "High Wind Watch issued January 13 at 1:13PM MST",
                    "description": "* WHAT...Southwest winds 40 to 50 mph.\n\n* WHERE...Rocky Mountain Front.",
                    "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ301"]
                }
            },
            {
                "properties": {
                    "headline": "Winter Storm Warning issued January 13 at 2:13PM MST",
                    "description": "* WHAT...Heavy snow expected.\n\n* WHERE...Northern Rocky Mountains.",
                    "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ999"]  # Non-local zone
                }
            }
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

    @patch('requests.get')
    def test_fetch_alerts_success(self, mock_get, weather_service, sample_api_response):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(sample_api_response)
        mock_get.return_value = mock_response

        result = weather_service.fetch_alerts()
        assert len(result) == 2
        assert "High Wind Watch" in result[0]['properties']['headline']

    @patch('requests.get')
    def test_fetch_alerts_retry_then_success(self, mock_get, weather_service, sample_api_response):
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
        alerts = sample_api_response['features']
        result = weather_service.filter_local_alerts(alerts)
        assert len(result) == 1
        assert "High Wind Watch" in result[0]['headline']

    def test_process_alerts(self, weather_service, sample_api_response):
        alerts = [{
            "headline": "High Wind Watch",
            "description": "* WHAT...Test alert",
            "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ301"]
        }]
        alerts[0]["headline"] = "High Wind Watch issued January 13 at 1:13PM MST"  # Add issued time
        result = weather_service.process_alerts(alerts)
        assert len(result) == 1
        assert isinstance(result[0], WeatherAlert)
        assert "High Wind Watch" in result[0].headline

    def test_process_alerts_deduplication(self, weather_service):
        # Create two alerts with same headline but different times
        alerts = [
            {
                "headline": "High Wind Watch issued January 13 at 1:13PM MST",
                "description": "* WHAT...Test 1",
                "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ301"]
            },
            {
                "headline": "High Wind Watch issued January 13 at 2:13PM MST",  # Later time
                "description": "* WHAT...Test 2",
                "affectedZones": ["https://api.weather.gov/zones/forecast/MTZ301"]
            }
        ]
        result = weather_service.process_alerts(alerts)
        assert len(result) == 1  # Should be deduplicated

class TestMainFunction:
    @patch.object(WeatherAlertService, 'fetch_alerts')
    def test_weather_alerts_success(self, mock_fetch, sample_api_response):
        mock_fetch.return_value = sample_api_response['features']
        result = weather_alerts()
        assert isinstance(result, str)
        assert "Weather Service" in result

    @patch.object(WeatherAlertService, 'fetch_alerts')
    def test_weather_alerts_no_alerts(self, mock_fetch):
        mock_fetch.return_value = []
        result = weather_alerts()
        assert result == ""

    @patch.object(WeatherAlertService, 'fetch_alerts')
    def test_weather_alerts_error_handling(self, mock_fetch):
        mock_fetch.side_effect = Exception("Test error")
        result = weather_alerts()
        assert result == ""