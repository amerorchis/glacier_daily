import types

import sunrise_timelapse.sleep_to_sunrise as sts


def test_sunrise_timelapse_complete_time(monkeypatch):
    # Patch sun.sun to return a fixed sunrise time
    from datetime import date, datetime

    class DummySun:
        def __getitem__(self, key):
            # Return a sunrise time 1 hour from now
            return datetime(2025, 5, 28, 6, 0, 0)

    monkeypatch.setattr(
        sts,
        "sun",
        types.SimpleNamespace(
            sun=lambda *a, **k: {"sunrise": DummySun().__getitem__(None)}
        ),
    )
    monkeypatch.setattr(sts, "ZoneInfo", lambda tz: None)
    monkeypatch.setattr(
        sts,
        "datetime",
        types.SimpleNamespace(
            now=lambda **kwargs: datetime(2025, 5, 28, 5, 0, 0),
            now_orig=datetime.now,
            today=lambda: date(2025, 5, 28),
        ),
    )
    monkeypatch.setattr(
        sts, "date", types.SimpleNamespace(today=lambda: date(2025, 5, 28))
    )
    result = sts.sunrise_timelapse_complete_time()
    assert isinstance(result, float)


def test_sleep_time_waits(monkeypatch):
    called = {}
    monkeypatch.setattr(sts, "sunrise_timelapse_complete_time", lambda: 0.1)
    monkeypatch.setattr(sts, "sleep", lambda t: called.setdefault("slept", t))
    sts.sleep_time()
    assert called["slept"] == 0.1
