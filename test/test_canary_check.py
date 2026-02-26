"""Tests for drip.canary_check module."""

import email.utils
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from drip.canary_check import (
    _is_today,
    check_canary_delivery,
    is_configured,
)


class TestIsConfigured:
    def test_not_configured_when_empty(self, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "")
        assert not is_configured()

    def test_not_configured_when_partial(self, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "")
        assert not is_configured()

    def test_configured_when_both_set(self, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")
        assert is_configured()


class TestIsToday:
    def test_matching_date(self):
        mtn = ZoneInfo("America/Denver")
        today = datetime(2026, 2, 25, 8, 0, tzinfo=mtn)
        date_str = email.utils.format_datetime(datetime(2026, 2, 25, 15, 0, tzinfo=UTC))
        assert _is_today(date_str, today)

    def test_different_date(self):
        mtn = ZoneInfo("America/Denver")
        today = datetime(2026, 2, 25, 8, 0, tzinfo=mtn)
        date_str = email.utils.format_datetime(datetime(2026, 2, 24, 15, 0, tzinfo=UTC))
        assert not _is_today(date_str, today)

    def test_invalid_date_string(self):
        mtn = ZoneInfo("America/Denver")
        today = datetime(2026, 2, 25, 8, 0, tzinfo=mtn)
        assert not _is_today("not a date", today)

    def test_empty_date_string(self):
        mtn = ZoneInfo("America/Denver")
        today = datetime(2026, 2, 25, 8, 0, tzinfo=mtn)
        assert not _is_today("", today)


def _make_header(from_addr="Glacier Daily <noreply@glacier.org>", date_str=None):
    """Build a raw RFC822 header bytes object for testing."""
    if date_str is None:
        date_str = email.utils.format_datetime(datetime(2026, 2, 25, 15, 0, tzinfo=UTC))
    return (
        f"From: {from_addr}\r\n"
        f"Subject: Glacier Daily Update\r\n"
        f"Date: {date_str}\r\n"
        f"\r\n"
    ).encode()


def _mock_imap(msg_ids=None, headers=None):
    """Create a mock IMAP4_SSL connection."""
    conn = MagicMock()
    conn.login.return_value = ("OK", [])
    conn.select.return_value = ("OK", [])

    if msg_ids is None:
        conn.search.return_value = ("OK", [b""])
    else:
        conn.search.return_value = ("OK", [b" ".join(msg_ids)])

    if headers:
        conn.fetch.side_effect = [("OK", [(b"1", h)]) for h in headers]
    else:
        conn.fetch.return_value = ("OK", [])

    conn.store.return_value = ("OK", [])
    conn.expunge.return_value = ("OK", [])
    conn.logout.return_value = ("BYE", [])
    return conn


class TestCheckCanaryDelivery:
    def test_skips_when_not_configured(self, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "")
        result = check_canary_delivery()
        assert not result.verified
        assert "skipped" in result.message

    @patch(
        "drip.canary_check.now_mountain",
        return_value=datetime(2026, 2, 25, 8, 0, tzinfo=ZoneInfo("America/Denver")),
    )
    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_verified_on_first_attempt(
        self, mock_sleep, mock_imap_cls, _mock_now, monkeypatch
    ):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        header = _make_header()
        conn = _mock_imap(msg_ids=[b"1"], headers=[header])
        mock_imap_cls.return_value = conn

        result = check_canary_delivery(wait_seconds=0, max_attempts=1, poll_interval=0)
        assert result.verified
        assert "attempt 1" in result.message
        conn.store.assert_called_once()
        conn.expunge.assert_called_once()

    @patch(
        "drip.canary_check.now_mountain",
        return_value=datetime(2026, 2, 25, 8, 0, tzinfo=ZoneInfo("America/Denver")),
    )
    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_verified_after_retry(
        self, mock_sleep, mock_imap_cls, _mock_now, monkeypatch
    ):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        header = _make_header()
        # First call: no messages; second call: message found
        conn_empty = _mock_imap()
        conn_found = _mock_imap(msg_ids=[b"1"], headers=[header])
        mock_imap_cls.side_effect = [conn_empty, conn_found]

        result = check_canary_delivery(wait_seconds=0, max_attempts=3, poll_interval=0)
        assert result.verified
        assert "attempt 2" in result.message

    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_not_found_after_all_attempts(self, mock_sleep, mock_imap_cls, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        conn = _mock_imap()
        mock_imap_cls.return_value = conn

        result = check_canary_delivery(wait_seconds=0, max_attempts=3, poll_interval=0)
        assert not result.verified
        assert "not received" in result.message

    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_handles_connection_error(self, mock_sleep, mock_imap_cls, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        mock_imap_cls.side_effect = OSError("Connection refused")

        result = check_canary_delivery(wait_seconds=0, max_attempts=2, poll_interval=0)
        assert not result.verified

    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_handles_login_error(self, mock_sleep, mock_imap_cls, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "wrong")

        conn = MagicMock()
        conn.login.side_effect = Exception("Authentication failed")
        mock_imap_cls.return_value = conn

        result = check_canary_delivery(wait_seconds=0, max_attempts=1, poll_interval=0)
        assert not result.verified

    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_ignores_non_glacier_emails(self, mock_sleep, mock_imap_cls, monkeypatch):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        header = _make_header(from_addr="spam@example.com")
        conn = _mock_imap(msg_ids=[b"1"], headers=[header])
        mock_imap_cls.return_value = conn

        result = check_canary_delivery(wait_seconds=0, max_attempts=1, poll_interval=0)
        assert not result.verified

    @patch("drip.canary_check.imaplib.IMAP4_SSL")
    @patch("drip.canary_check.time.sleep")
    def test_initial_wait_uses_wait_seconds(
        self, mock_sleep, mock_imap_cls, monkeypatch
    ):
        monkeypatch.setenv("CANARY_EMAIL", "test@gmail.com")
        monkeypatch.setenv("CANARY_IMAP_PASSWORD", "secret")

        conn = _mock_imap()
        mock_imap_cls.return_value = conn

        check_canary_delivery(wait_seconds=42, max_attempts=1, poll_interval=0)
        # First sleep call should be the initial wait
        mock_sleep.assert_any_call(42)
