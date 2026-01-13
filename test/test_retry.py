"""
Unit tests for shared.retry module.

Tests the retry decorator functionality including retries, backoff, and exception handling.
"""

import pytest

import shared.retry as retry_mod


class TestRetryDecorator:
    """Tests for the retry decorator."""

    def test_success_on_first_try(self):
        """Verify function returns normally when no exception is raised."""

        @retry_mod.retry(times=3, exceptions=(ValueError,))
        def f(x):
            return x + 1

        assert f(1) == 2

    def test_retries_on_matching_exception(self, monkeypatch):
        """Verify function retries the specified number of times."""
        calls = []

        @retry_mod.retry(times=2, exceptions=(ValueError,), default="fail", backoff=0)
        def f():
            calls.append(1)
            raise ValueError("fail")

        assert f() == "fail"
        assert len(calls) == 2

    def test_non_matching_exception_propagates(self):
        """Verify non-matching exceptions propagate immediately without retry."""
        calls = []

        @retry_mod.retry(times=3, exceptions=(ValueError,))
        def f():
            calls.append(1)
            raise TypeError("not retried")

        with pytest.raises(TypeError, match="not retried"):
            f()

        # Should only be called once - exception propagates immediately
        assert len(calls) == 1

    def test_backoff_timing(self, monkeypatch):
        """Verify backoff sleep is called with correct duration."""
        sleep_calls = []
        monkeypatch.setattr("shared.retry.sleep", lambda x: sleep_calls.append(x))

        @retry_mod.retry(times=3, exceptions=(ValueError,), default="fail", backoff=5)
        def f():
            raise ValueError()

        f()

        # Should sleep after each failed attempt (3 times total)
        assert sleep_calls == [5, 5, 5]

    def test_default_backoff_value(self, monkeypatch):
        """Verify default backoff of 15 seconds is used."""
        sleep_calls = []
        monkeypatch.setattr("shared.retry.sleep", lambda x: sleep_calls.append(x))

        @retry_mod.retry(times=2, exceptions=(ValueError,), default="fail")
        def f():
            raise ValueError()

        f()

        # Default backoff is 15
        assert sleep_calls == [15, 15]

    def test_args_forwarding(self):
        """Verify positional arguments are passed to wrapped function."""

        @retry_mod.retry(times=1, exceptions=(ValueError,))
        def f(a, b, c):
            return a + b + c

        assert f(1, 2, 3) == 6

    def test_kwargs_forwarding(self):
        """Verify keyword arguments are passed to wrapped function."""

        @retry_mod.retry(times=1, exceptions=(ValueError,))
        def f(a, b=None, c=None):
            return (a, b, c)

        assert f(1, b=2, c=3) == (1, 2, 3)

    def test_mixed_args_kwargs_forwarding(self):
        """Verify mixed positional and keyword arguments work correctly."""

        @retry_mod.retry(times=1, exceptions=(ValueError,))
        def f(*args, **kwargs):
            return (args, kwargs)

        result = f(1, 2, x=3, y=4)
        assert result == ((1, 2), {"x": 3, "y": 4})

    def test_multiple_exception_types(self, monkeypatch):
        """Verify retry works with multiple exception types."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)
        calls = []
        exceptions = [ValueError("first"), TypeError("second"), KeyError("third")]

        @retry_mod.retry(
            times=4, exceptions=(ValueError, TypeError, KeyError), default="fail"
        )
        def f():
            calls.append(1)
            if exceptions:
                raise exceptions.pop(0)
            return "success"

        result = f()
        assert result == "success"
        assert len(calls) == 4  # 3 failures + 1 success

    def test_returns_default_after_exhausted_retries(self, monkeypatch):
        """Verify default value returned after all retries exhausted."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)

        @retry_mod.retry(times=2, exceptions=(ValueError,), default="default_value")
        def f():
            raise ValueError()

        assert f() == "default_value"

    def test_empty_string_default(self, monkeypatch):
        """Verify empty string default works correctly."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)

        @retry_mod.retry(times=1, exceptions=(ValueError,), default="")
        def f():
            raise ValueError()

        assert f() == ""

    def test_prints_retry_message(self, monkeypatch, capsys):
        """Verify retry attempts are logged to stdout."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)

        @retry_mod.retry(times=2, exceptions=(ValueError,), default="fail")
        def f():
            raise ValueError()

        f()
        captured = capsys.readouterr()

        # Should print message for each retry attempt
        assert "attempt" in captured.out.lower()
        assert "1 of 2" in captured.out
        assert "2 of 2" in captured.out

    def test_single_retry(self, monkeypatch):
        """Verify single retry attempt works correctly."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)
        calls = []

        @retry_mod.retry(times=1, exceptions=(ValueError,), default="fail")
        def f():
            calls.append(1)
            raise ValueError()

        result = f()
        assert result == "fail"
        assert len(calls) == 1

    def test_success_after_initial_failure(self, monkeypatch):
        """Verify function can succeed after initial failures."""
        monkeypatch.setattr("shared.retry.sleep", lambda x: None)
        attempts = [0]

        @retry_mod.retry(times=3, exceptions=(ValueError,))
        def f():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("retry")
            return "success"

        result = f()
        assert result == "success"
        assert attempts[0] == 2
