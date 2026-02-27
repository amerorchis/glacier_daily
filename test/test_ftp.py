import ftplib
from datetime import datetime
from unittest.mock import mock_open, patch

import pytest

import shared.ftp as ftp_mod
from shared.ftp import FTPSession


def _make_delete_ftp(
    files, sendcmd_response="213 20240101000000", *, dir_names=frozenset()
):
    """Create a DummyFTP and deleted-file tracker for delete_on_first tests."""
    deleted = []

    class DummyFTP:
        def nlst(self):
            return list(files)

        def size(self, f):
            if f in dir_names:
                raise ftplib.error_perm("550 not a file")
            return 1

        def sendcmd(self, cmd):
            return sendcmd_response

        def delete(self, f):
            deleted.append(f)

    return DummyFTP(), deleted


def test_delete_on_first(monkeypatch):
    ftp, deleted = _make_delete_ftp(["file1", "file2"])
    monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 1))
    ftp_mod.delete_on_first(ftp)
    assert deleted == ["file1", "file2"]


def test_delete_on_first_not_first_of_month(monkeypatch):
    """Should return early on non-1st day without listing files."""
    called = {"nlst": False}

    class DummyFTP:
        def nlst(self):
            called["nlst"] = True
            return []

    monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))
    ftp_mod.delete_on_first(DummyFTP())
    assert not called["nlst"]


def test_delete_on_first_skips_directories(monkeypatch):
    """Directories (ftplib.error_perm on size()) should be skipped."""
    ftp, deleted = _make_delete_ftp(
        ["a_directory", "old_file"], dir_names={"a_directory"}
    )
    monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 1))
    ftp_mod.delete_on_first(ftp)
    assert "a_directory" not in deleted
    assert "old_file" in deleted


def test_delete_on_first_keeps_recent_files(monkeypatch):
    """Files newer than 6 months should not be deleted."""
    # Date within 6 months of the mocked "today" (2025-05-01)
    ftp, deleted = _make_delete_ftp(["recent_file"], "213 20250430000000")
    monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 1))
    ftp_mod.delete_on_first(ftp)
    assert "recent_file" not in deleted


@pytest.mark.usefixtures("mock_required_settings")
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
        monkeypatch.setenv("FTP_USERNAME", "u")
        monkeypatch.setenv("FTP_PASSWORD", "p")
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
        monkeypatch.setenv("FTP_USERNAME", "u")
        monkeypatch.setenv("FTP_PASSWORD", "p")
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
        monkeypatch.setenv("FTP_USERNAME", "u")
        monkeypatch.setenv("FTP_PASSWORD", "p")
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
        monkeypatch.setenv("FTP_USERNAME", "u")
        monkeypatch.setenv("FTP_PASSWORD", "p")
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with pytest.raises(RuntimeError), FTPSession() as _session:
            raise RuntimeError("test error")

        assert dummy.quit_called

    def test_session_upload_without_file(self, monkeypatch):
        """Test FTPSession.upload with file=None (list only)."""
        dummy = self._make_dummy_ftp()
        monkeypatch.setattr(ftp_mod, "FTP", lambda server: dummy)
        monkeypatch.setenv("FTP_USERNAME", "u")
        monkeypatch.setenv("FTP_PASSWORD", "p")
        monkeypatch.setattr(ftp_mod, "now_mountain", lambda: datetime(2025, 5, 15))

        with FTPSession() as session:
            url, files = session.upload("dir", "file.txt")

        assert url == ""
        assert "file1" in files
