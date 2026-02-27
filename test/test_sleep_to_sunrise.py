from datetime import date, datetime
from unittest.mock import MagicMock

import sunrise_timelapse.sleep_to_sunrise as sts


def test_sunrise_timelapse_complete_time(monkeypatch):
    sunrise = datetime(2025, 5, 28, 6, 0, 0)
    now = datetime(2025, 5, 28, 5, 0, 0)

    mock_sun = MagicMock()
    mock_sun.sun.return_value = {"sunrise": sunrise}
    monkeypatch.setattr(sts, "sun", mock_sun)

    mock_dt = MagicMock()
    mock_dt.now.return_value = now
    monkeypatch.setattr(sts, "datetime", mock_dt)

    mock_date = MagicMock()
    mock_date.today.return_value = date(2025, 5, 28)
    monkeypatch.setattr(sts, "date", mock_date)

    monkeypatch.setattr(sts, "ZoneInfo", lambda tz: None)

    result = sts.sunrise_timelapse_complete_time()
    assert result == 6720.0  # 1 hour to sunrise + 52 min buffer


def test_sleep_time_waits(monkeypatch):
    called = {}
    monkeypatch.setattr(sts, "sunrise_timelapse_complete_time", lambda: 0.1)
    monkeypatch.setattr(sts, "sleep", lambda t: called.setdefault("slept", t))
    sts.sleep_time()
    assert called["slept"] == 0.1
