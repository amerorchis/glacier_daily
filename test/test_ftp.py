import ftplib
import types as _types
from datetime import datetime, timedelta
from unittest.mock import mock_open, patch

import pytest

import shared.ftp as ftp_mod
from shared.ftp import FTPSession


def test_delete_on_first(monkeypatch):
    class DummyFTP:
        def __init__(self):
            self.deleted = None

        def nlst(self):
            return ["file1", "file2"]

        def size(self, f):
            return 1

        def sendcmd(self, cmd):
            return "213 20240101000000"

        def delete(self, f):
            self.deleted = f

    dummy = DummyFTP()
    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 1), strptime=datetime.strptime
        ),
    )
    ftp_mod.delete_on_first(dummy)
    # Should attempt to delete files if first of month


def test_delete_on_first_not_first_of_month(monkeypatch):
    """Should return early on non-1st day without listing files."""
    called = {"nlst": False}

    class DummyFTP:
        def nlst(self):
            called["nlst"] = True
            return []

    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 15), strptime=datetime.strptime
        ),
    )
    ftp_mod.delete_on_first(DummyFTP())
    assert not called["nlst"]


def test_delete_on_first_skips_directories(monkeypatch):
    """Directories (ftplib.error_perm on size()) should be skipped."""
    deleted = []

    class DummyFTP:
        def nlst(self):
            return ["a_directory", "old_file"]

        def size(self, f):
            if f == "a_directory":
                raise ftplib.error_perm("550 not a file")
            return 1

        def sendcmd(self, cmd):
            return "213 20240101000000"

        def delete(self, f):
            deleted.append(f)

    monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 1))
    ftp_mod.delete_on_first(DummyFTP())
    assert "a_directory" not in deleted
    assert "old_file" in deleted


def test_delete_on_first_keeps_recent_files(monkeypatch):
    """Files newer than 6 months should not be deleted."""
    deleted = []

    class DummyFTP:
        def nlst(self):
            return ["recent_file"]

        def size(self, f):
            return 1

        def sendcmd(self, cmd):
            # Return a recent date (yesterday)
            yesterday = datetime.now() - timedelta(days=1)
            return f"213 {yesterday.strftime('%Y%m%d%H%M%S')}"

        def delete(self, f):
            deleted.append(f)

    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 1), strptime=datetime.strptime
        ),
    )
    ftp_mod.delete_on_first(DummyFTP())
    assert "recent_file" not in deleted


def test_upload_file(monkeypatch):
    class DummyFTP:
        def __init__(self):
            self.deleted = None

        def login(self, u, p):
            pass

        def cwd(self, d):
            pass

        def storbinary(self, cmd, f):
            pass

        def nlst(self):
            return ["file1"]

        def quit(self):
            pass

        def size(self, f):
            return 1

        def sendcmd(self, cmd):
            return "213 20240101000000"

        def delete(self, f):
            self.deleted = f

        def rename(self, old_name, new_name):
            pass

    monkeypatch.setattr(ftp_mod, "FTP", lambda server: DummyFTP())
    monkeypatch.setattr(
        ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
    )
    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 1), strptime=datetime.strptime
        ),
    )

    with patch("builtins.open", mock_open(read_data=b"data")):
        url, files = ftp_mod.upload_file("dir", "file.txt", "local.txt")
    assert url.startswith("https://glacier.org/")
    assert "file1" in files


def test_upload_file_storbinary_exception(monkeypatch):
    """When storbinary raises, exception is caught and returns empty url/files."""

    class DummyFTP:
        def login(self, u, p):
            pass

        def cwd(self, d):
            pass

        def storbinary(self, cmd, f):
            raise OSError("connection reset")

        def nlst(self):
            return ["file1"]

        def quit(self):
            pass

        def size(self, f):
            return 1

        def sendcmd(self, cmd):
            return "213 20240101000000"

        def delete(self, f):
            pass

        def rename(self, old_name, new_name):
            pass

    monkeypatch.setattr(ftp_mod, "FTP", lambda server: DummyFTP())
    monkeypatch.setattr(
        ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
    )
    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 15), strptime=datetime.strptime
        ),
    )

    with patch("builtins.open", mock_open(read_data=b"data")):
        url, files = ftp_mod.upload_file("dir", "file.txt", "local.txt")
    assert url == ""
    assert files == []


def test_upload_file_no_file_param(monkeypatch):
    """When file param is None, should skip upload but still list files."""

    class DummyFTP:
        def login(self, u, p):
            pass

        def cwd(self, d):
            pass

        def nlst(self):
            return ["existing.txt"]

        def quit(self):
            pass

        def size(self, f):
            return 1

        def sendcmd(self, cmd):
            return "213 20240101000000"

        def delete(self, f):
            pass

        def rename(self, old_name, new_name):
            pass

    monkeypatch.setattr(ftp_mod, "FTP", lambda server: DummyFTP())
    monkeypatch.setattr(
        ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
    )
    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 15), strptime=datetime.strptime
        ),
    )
    url, files = ftp_mod.upload_file("dir", "file.txt")
    assert url == ""
    assert "existing.txt" in files


class TestFTPSession:
    """Tests for the FTPSession context manager."""

    def _make_dummy_ftp(self):
        class DummyFTP:
            def __init__(self):
                self.cwd_calls = []
                self.quit_called = False

            def login(self, u, p):
                pass

            def cwd(self, d):
                self.cwd_calls.append(d)

            def storbinary(self, cmd, f):
                pass

            def nlst(self):
                return ["file1"]

            def quit(self):
                self.quit_called = True

            def size(self, f):
                return 1

            def sendcmd(self, cmd):
                return "213 20240101000000"

            def delete(self, f):
                pass

            def rename(self, old_name, new_name):
                pass

        return DummyFTP()

    def test_session_upload(self, monkeypatch):
        """Test basic upload through FTPSession."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setattr(
            ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
        )
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with (
            FTPSession() as session,
            patch("builtins.open", mock_open(read_data=b"data")),
        ):
            url, files = session.upload("dir", "file.txt", "local.txt")

        assert url.startswith("https://glacier.org/")
        assert "file1" in files
        assert dummy.quit_called

    def test_session_resets_cwd_to_root(self, monkeypatch):
        """Test that each upload resets to root before changing directory."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setattr(
            ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
        )
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with (
            FTPSession() as session,
            patch("builtins.open", mock_open(read_data=b"data")),
        ):
            session.upload("dir1", "a.txt", "local.txt")
            session.upload("dir2", "b.txt", "local.txt")

        assert dummy.cwd_calls == ["/", "dir1", "/", "dir2"]

    def test_delete_on_first_runs_once_per_dir(self, monkeypatch):
        """Test that delete_on_first runs only once per directory."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setattr(
            ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
        )
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        delete_count = {"count": 0}

        def counting_delete(ftp):
            delete_count["count"] += 1

        monkeypatch.setattr(ftp_mod, "delete_on_first", counting_delete)

        with (
            FTPSession() as session,
            patch("builtins.open", mock_open(read_data=b"data")),
        ):
            session.upload("dir1", "a.txt", "local.txt")
            session.upload("dir1", "b.txt", "local.txt")
            session.upload("dir2", "c.txt", "local.txt")

        assert delete_count["count"] == 2

    def test_session_closes_on_exception(self, monkeypatch):
        """Test that FTPSession closes connection even on upload error."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setattr(
            ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
        )
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with pytest.raises(RuntimeError), FTPSession() as _session:
            raise RuntimeError("test error")

        assert dummy.quit_called

    def test_session_upload_without_file(self, monkeypatch):
        """Test FTPSession.upload with file=None (list only)."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setattr(
            ftp_mod.os, "environ", {"FTP_USERNAME": "u", "FTP_PASSWORD": "p"}
        )
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with FTPSession() as session:
            url, files = session.upload("dir", "file.txt")

        assert url == ""
        assert "file1" in files
