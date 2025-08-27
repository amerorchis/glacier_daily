from datetime import datetime

import shared.ftp as ftp_mod


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
    import types as _types

    monkeypatch.setattr(
        ftp_mod,
        "datetime",
        _types.SimpleNamespace(
            now=lambda: datetime(2025, 5, 1), strptime=datetime.strptime
        ),
    )
    ftp_mod.delete_on_first(dummy)
    # Should attempt to delete files if first of month


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

    import types as _types

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
    import builtins
    from unittest.mock import mock_open, patch

    with patch("builtins.open", mock_open(read_data=b"data")):
        url, files = ftp_mod.upload_file("dir", "file.txt", "local.txt")
    assert url.startswith("https://glacier.org/")
    assert "file1" in files
