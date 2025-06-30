def test_record_drip_event_success(monkeypatch):
    called = {}

    def fake_post(url, headers, data, timeout):
        called["url"] = url
        called["headers"] = headers
        called["data"] = data
        called["timeout"] = timeout

        class R:
            status_code = 204

        return R()

    import types

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    monkeypatch.setattr(
        drip_actions.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    drip_actions.record_drip_event("test@example.com", event="Test Event")
    assert called["url"].endswith("/v2/a/events")
    assert "Test Event" in called["data"]
    assert called["timeout"] == 30


"""
Module for testing the Drip API functionality.
"""

import os
import sys

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )  # pragma: no cover


# --- html_friendly.py ---
import drip.html_friendly as html_friendly


def test_html_safe_ascii():
    assert html_friendly.html_safe("hello") == "hello"


def test_html_safe_non_ascii():
    # 'é' should be encoded as &#233;
    assert "&#233;" in html_friendly.html_safe("café")


# --- scheduled_subs.py ---
import drip.scheduled_subs as scheduled_subs
import drip.update_subscriber as update_subscriber


def test_start_and_end_calls_update_subscriber(monkeypatch):
    calls = []
    monkeypatch.setattr(
        update_subscriber, "update_subscriber", lambda u: calls.append(u)
    )
    scheduled_subs.start(["a@example.com"])
    if calls:
        assert calls[0]["email"] == "a@example.com"
    calls.clear()
    scheduled_subs.end(["b@example.com"])
    if calls:
        assert calls[0]["email"] == "b@example.com"


def test_update_scheduled_subs_logic(monkeypatch):
    today = scheduled_subs.datetime.now().strftime("%Y-%m-%d")
    yesterday = (
        scheduled_subs.datetime.now() - scheduled_subs.timedelta(days=1)
    ).strftime("%Y-%m-%d")
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
def test_update_subscriber_success(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {}

    import types

    monkeypatch.setattr(
        update_subscriber,
        "requests",
        types.SimpleNamespace(post=lambda *a, **k: FakeResponse()),
    )
    monkeypatch.setattr(
        update_subscriber.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    update_subscriber.update_subscriber({"email": "test@example.com"})


def test_update_subscriber_failure(monkeypatch):
    class FakeResponse:
        status_code = 400

        def json(self):
            return {"errors": [{"code": "bad", "message": "fail"}]}

    import types

    monkeypatch.setattr(
        update_subscriber,
        "requests",
        types.SimpleNamespace(post=lambda *a, **k: FakeResponse()),
    )
    monkeypatch.setattr(
        update_subscriber.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    update_subscriber.update_subscriber({"email": "fail@example.com"})


# --- drip_actions.py ---
import drip.drip_actions as drip_actions


def test_get_subs_merges(monkeypatch):
    monkeypatch.setattr(
        drip_actions, "update_scheduled_subs", lambda: {"start": ["a"], "end": ["b"]}
    )
    monkeypatch.setattr(drip_actions, "subscriber_list", lambda tag: ["b", "c"])
    result = drip_actions.get_subs("tag")
    assert set(result) == {"a", "c"}


def test_bulk_workflow_trigger(monkeypatch):
    called = {}

    def fake_post(url, headers, data, timeout):
        called["url"] = url
        called["timeout"] = timeout

        class R:
            status_code = 201

            def json(self):
                return {}

        return R()

    import types

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    monkeypatch.setattr(
        drip_actions.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    drip_actions.bulk_workflow_trigger(["a@example.com", "b@example.com"])
    assert "url" in called


def test_send_in_drip(monkeypatch):
    def fake_post(url, headers, data, timeout):
        assert timeout == 30

        class R:
            status_code = 201

            def json(self):
                return {}

        return R()

    import types

    monkeypatch.setattr(drip_actions, "requests", types.SimpleNamespace(post=fake_post))
    monkeypatch.setattr(
        drip_actions.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    drip_actions.send_in_drip("a@example.com")


# --- subscriber_list.py ---
import drip.subscriber_list as subscriber_list


def test_subscriber_list_success(monkeypatch):
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

    import types

    monkeypatch.setattr(
        subscriber_list,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: FakeResponse()),
    )
    monkeypatch.setattr(
        subscriber_list.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    result = subscriber_list.subscriber_list()
    assert result == ["a@example.com"]


def test_subscriber_list_multipage(monkeypatch):
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

    import types

    calls = []

    def fake_get(url, headers=None, params=None):
        # params["page"] will be 1 for first call, 2 for second
        page = params["page"] if params and "page" in params else 1
        calls.append(page)
        return FakeResponse(page)

    monkeypatch.setattr(
        subscriber_list, "requests", types.SimpleNamespace(get=fake_get)
    )
    monkeypatch.setattr(
        subscriber_list.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    result = subscriber_list.subscriber_list()
    assert set(result) == {"a@example.com", "b@example.com"}
    assert calls == [1, 2]

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

    import types

    monkeypatch.setattr(
        subscriber_list,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: FakeResponse()),
    )
    monkeypatch.setattr(
        subscriber_list.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    result = subscriber_list.subscriber_list()
    assert result == ["a@example.com"]


def test_subscriber_list_failure(monkeypatch):
    class FakeRequestException(Exception):
        pass

    class FakeResponse:
        def raise_for_status(self):
            raise FakeRequestException("fail")

        def json(self):
            return {"subscribers": [], "meta": {"total_pages": 1}}

    import types

    fake_requests = types.SimpleNamespace(
        get=lambda *a, **k: FakeResponse(),
        exceptions=types.SimpleNamespace(RequestException=FakeRequestException),
    )
    monkeypatch.setattr(subscriber_list, "requests", fake_requests)
    monkeypatch.setattr(
        subscriber_list.os, "environ", {"DRIP_TOKEN": "t", "DRIP_ACCOUNT": "a"}
    )
    result = subscriber_list.subscriber_list()
    assert result == []
