import os
import sys

import pytest

from shared.lock import acquire_lock, release_lock

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="fcntl-based locking is Unix-only"
)


@pytest.fixture(autouse=True)
def _clean_lock(tmp_path, monkeypatch):
    """Point LOCK_FILE at a temp directory so tests don't conflict."""
    lock_path = tmp_path / "test.lock"
    monkeypatch.setattr("shared.lock.LOCK_FILE", lock_path)
    yield
    lock_path.unlink(missing_ok=True)


def test_acquire_release_roundtrip(tmp_path, monkeypatch):
    lock_path = tmp_path / "test.lock"
    monkeypatch.setattr("shared.lock.LOCK_FILE", lock_path)

    fd = acquire_lock()
    assert fd is not None
    assert lock_path.exists()

    release_lock(fd)
    assert not lock_path.exists()


def test_lock_file_contains_pid(tmp_path, monkeypatch):
    lock_path = tmp_path / "test.lock"
    monkeypatch.setattr("shared.lock.LOCK_FILE", lock_path)

    fd = acquire_lock()
    assert fd is not None
    content = lock_path.read_text()
    assert content == str(os.getpid())
    release_lock(fd)


def test_double_acquire_returns_none(tmp_path, monkeypatch):
    lock_path = tmp_path / "test.lock"
    monkeypatch.setattr("shared.lock.LOCK_FILE", lock_path)

    fd1 = acquire_lock()
    assert fd1 is not None

    fd2 = acquire_lock()
    assert fd2 is None

    release_lock(fd1)


def test_release_none_is_noop():
    release_lock(None)  # Should not raise
