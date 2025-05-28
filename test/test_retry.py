import pytest

import shared.retry as retry_mod


def test_retry_success():
    @retry_mod.retry(times=3, exceptions=(ValueError,))
    def f(x):
        return x + 1

    assert f(1) == 2


def test_retry_retries(monkeypatch):
    calls = []

    @retry_mod.retry(times=2, exceptions=(ValueError,), default="fail", backoff=0)
    def f():
        calls.append(1)
        raise ValueError("fail")

    assert f() == "fail"
    assert len(calls) == 2
