"""
Module for testing the Drip API functionality.
"""

import types

import drip.drip_actions as drip_actions
import drip.scheduled_subs as scheduled_subs
import drip.subscriber_list as subscriber_list
import drip.update_subscriber as update_subscriber


def _set_drip_env(monkeypatch):
    """Helper to set the Drip env vars used by tests."""
    monkeypatch.setenv("DRIP_TOKEN", "t")
    monkeypatch.setenv("DRIP_ACCOUNT", "a")


# --- scheduled_subs.py ---


def test_start_and_end_calls_update_subscriber(monkeypatch):
    calls = []
    # Patch the function in the scheduled_subs module namespace, not the original module
    monkeypatch.setattr(scheduled_subs, "update_subscriber", lambda u: calls.append(u))
    scheduled_subs.start(["a@example.com"])
    assert len(calls) == 1
    assert calls[0]["email"] == "a@example.com"
    calls.clear()
    scheduled_subs.end(["b@example.com"])
    assert len(calls) == 1
    assert calls[0]["email"] == "b@example.com"


def test_update_scheduled_subs_logic(monkeypatch):
    from shared.datetime_utils import now_mountain

    today = now_mountain().strftime("%Y-%m-%d")
    yesterday = (now_mountain() - scheduled_subs.timedelta(days=1)).strftime("%Y-%m-%d")
    fake_list = [
        {
            "tags": ["Daily Start Set"],
            "email": "start@example.com",
            "custom_fields": {"Daily_Start": today},
        },
        {
            "tags": ["Daily End Set"],
            "email": "end@example.com",
            "custom_fields": {"Daily_End": yesterday},
        },
    ]
    monkeypatch.setattr(scheduled_subs, "subscriber_list", lambda tags: fake_list)
    monkeypatch.setattr(scheduled_subs, "start", lambda subs: None)
    monkeypatch.setattr(scheduled_subs, "end", lambda subs: None)
    updates = scheduled_subs.update_scheduled_subs()
    assert "start@example.com" in updates["start"]
    assert "end@example.com" in updates["end"]


# --- update_subscriber.py ---
def test_update_subscriber_success(monkeypatch, mock_required_settings):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {}

    monkeypatch.setattr(
        update_subscriber,
        "requests",
        types.SimpleNamespace(post=lambda *a, **k: FakeResponse()),
    )
    _set_drip_env(monkeypatch)
    update_subscriber.update_subscriber({"email": "test@example.com"})


def test_update_subscriber_failure(monkeypatch, mock_required_settings):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {"errors": [{"code": "bad", "message": "fail"}]}

    monkeypatch.setattr(
        update_subscriber,
        "requests",
        types.SimpleNamespace(post=lambda *a, **k: FakeResponse()),
    )
    _set_drip_env(monkeypatch)
    update_subscriber.update_subscriber({"email": "fail@example.com"})


# --- drip_actions.py ---


def test_get_subs_merges(monkeypatch):
    monkeypatch.setattr(
        drip_actions, "update_scheduled_subs", lambda: {"start": ["a"], "end": ["b"]}
    )
    monkeypatch.setattr(drip_actions, "subscriber_list", lambda tag: ["b", "c"])
    result = drip_actions.get_subs("tag")
    assert set(result) == {"a", "c"}


def test_bulk_workflow_trigger(monkeypatch, mock_required_settings):
    called = {}

    def fake_post(url, headers, data, timeout):
        called["url"] = url
        called["timeout"] = timeout

        class R:
            status_code = 201

            def json(self):
                return {}

        return R()

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    _set_drip_env(monkeypatch)
    drip_actions.bulk_workflow_trigger(["a@example.com", "b@example.com"])
    assert "url" in called


def test_bulk_workflow_trigger_chunking(monkeypatch, mock_required_settings):
    """Verify >1000 subscribers are chunked into batches of 1000."""
    post_calls = []

    def fake_post(url, headers, data, timeout):
        post_calls.append(data)

        class R:
            status_code = 201

            def json(self):
                return {}

        return R()

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    _set_drip_env(monkeypatch)
    subs = [f"user{i}@example.com" for i in range(2500)]
    drip_actions.bulk_workflow_trigger(subs)
    assert len(post_calls) == 3  # 1000 + 1000 + 500


def test_bulk_workflow_trigger_failure(monkeypatch, mock_required_settings, caplog):
    """Verify non-201 status logs an error."""

    def fake_post(url, headers, data, timeout):
        class R:
            status_code = 422

            def json(self):
                return {"errors": [{"code": "invalid", "message": "bad data"}]}

        return R()

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    _set_drip_env(monkeypatch)
    with caplog.at_level("ERROR"):
        drip_actions.bulk_workflow_trigger(["a@example.com"])
    assert "Failed to add subscribers" in caplog.text


# --- subscriber_list.py ---


def test_subscriber_list_success(monkeypatch, mock_required_settings):
    class FakeResponse:
        def __init__(self):
            self._page = 1

        def json(self):
            return {
                "subscribers": [{"email": "a@example.com"}],
                "meta": {"total_pages": 1},
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        subscriber_list,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: FakeResponse()),
    )
    _set_drip_env(monkeypatch)
    result = subscriber_list.subscriber_list()
    assert result == ["a@example.com"]


def test_subscriber_list_multipage(monkeypatch, mock_required_settings):
    class FakeResponse:
        def __init__(self, page):
            self.page = page

        def json(self):
            if self.page == 1:
                return {
                    "subscribers": [{"email": "a@example.com"}],
                    "meta": {"total_pages": 2},
                }
            else:
                return {
                    "subscribers": [{"email": "b@example.com"}],
                    "meta": {"total_pages": 2},
                }

        def raise_for_status(self):
            pass

    calls = []

    def fake_get(url, headers=None, params=None, **kwargs):
        # params["page"] will be 1 for first call, 2 for second
        page = params["page"] if params and "page" in params else 1
        calls.append(page)
        return FakeResponse(page)

    monkeypatch.setattr(
        subscriber_list, "requests", types.SimpleNamespace(get=fake_get)
    )
    _set_drip_env(monkeypatch)
    result = subscriber_list.subscriber_list()
    assert set(result) == {"a@example.com", "b@example.com"}
    assert calls == [1, 2]

    class FakeSimpleResponse:
        def __init__(self):
            self._page = 1

        def json(self):
            return {
                "subscribers": [{"email": "a@example.com"}],
                "meta": {"total_pages": 1},
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        subscriber_list,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: FakeSimpleResponse()),
    )
    result = subscriber_list.subscriber_list()
    assert result == ["a@example.com"]


def test_subscriber_list_returns_full_objects(monkeypatch, mock_required_settings):
    """Verify non-email-only tags return full subscriber dicts."""

    class FakeResponse:
        def json(self):
            return {
                "subscribers": [
                    {"email": "a@example.com", "tags": ["Daily Start Set"]}
                ],
                "meta": {"total_pages": 1},
            }

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        subscriber_list,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: FakeResponse()),
    )
    _set_drip_env(monkeypatch)
    result = subscriber_list.subscriber_list(tag="Daily Start Set")
    assert isinstance(result[0], dict)
    assert result[0]["email"] == "a@example.com"


def test_subscriber_list_failure(monkeypatch, mock_required_settings):
    class FakeRequestException(Exception):
        pass

    class FakeResponse:
        def raise_for_status(self):
            raise FakeRequestException("fail")

        def json(self):
            return {"subscribers": [], "meta": {"total_pages": 1}}

    fake_requests = types.SimpleNamespace(
        get=lambda *a, **k: FakeResponse(),
        exceptions=types.SimpleNamespace(RequestException=FakeRequestException),
    )
    monkeypatch.setattr(subscriber_list, "requests", fake_requests)
    _set_drip_env(monkeypatch)
    result = subscriber_list.subscriber_list()
    assert result == []
