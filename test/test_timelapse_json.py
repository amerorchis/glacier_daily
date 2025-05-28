import json
from datetime import datetime

import pytest

import sunrise_timelapse.timelapse_json as tj


# --- gen_json ---
def test_gen_json_basic():
    files = [
        "5_28_2025_sunrise_timelapse.mp4",
        "5_27_2025_sunrise_timelapse.mp4",
        ".",
        "..",
    ]
    result = tj.gen_json(files.copy())
    data = json.loads(result)
    assert isinstance(data, list)
    assert data[0]["date"].startswith(str(datetime.now().year)) or "date" in data[0]
    # The first entry is just the date, skip it
    assert any("5-28 Sunrise Timelapse" in d.get("title", "") for d in data[1:])
    assert any("5-27 Sunrise Timelapse" in d.get("title", "") for d in data[1:])


def test_gen_json_raises_on_empty():
    files = [".", ".."]
    with pytest.raises(ValueError):
        tj.gen_json(files.copy())


def test_gen_json_raises_on_malformed():
    files = ["5_28_sunrise_timelapse.mp4", ".", ".."]
    with pytest.raises((IndexError, ValueError, TypeError)):
        tj.gen_json(files.copy())


# --- send_timelapse_data ---
def test_send_timelapse_data_success(monkeypatch):
    class FakeFTP:
        def __init__(self, server):
            self.server = server

        def login(self, u, p):
            pass

        def storbinary(self, cmd, buf):
            pass

        def quit(self):
            pass

    monkeypatch.setattr(tj, "FTP", FakeFTP)
    monkeypatch.setattr(tj, "sleep", lambda x: None)
    monkeypatch.setattr(
        tj.os,
        "environ",
        {"webcam_ftp_user": "u", "webcam_ftp_pword": "p", "timelapse_server": "s"},
    )
    data = '[{"date": "2025-05-28"}]'
    url = tj.send_timelapse_data(data)
    assert url.startswith("https://glacier.org/webcam-timelapse/")


def test_send_timelapse_data_failure(monkeypatch):
    class FakeFTP:
        def __init__(self, server):
            raise tj.socket.gaierror

    monkeypatch.setattr(tj, "FTP", FakeFTP)
    monkeypatch.setattr(tj, "sleep", lambda x: None)
    monkeypatch.setattr(
        tj.os,
        "environ",
        {"webcam_ftp_user": "u", "webcam_ftp_pword": "p", "timelapse_server": "s"},
    )
    # After sleep, will raise again, so should hit except and propagate
    with pytest.raises(tj.socket.gaierror):
        tj.send_timelapse_data('[{"date": "2025-05-28"}]')
