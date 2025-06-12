import base64
import json
from datetime import datetime

import shared.retrieve_from_json as rfj


def test_retrieve_from_json_found(tmp_path, monkeypatch):
    # Prepare a fake email.json
    today = datetime.now().strftime("%Y-%m-%d")
    data = {"date": today, "foo": base64.b64encode(b"bar").decode("utf-8")}
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    with open(server_dir / "email.json", "w", encoding="utf8") as f:
        json.dump(data, f)
    monkeypatch.chdir(tmp_path)
    found, values = rfj.retrieve_from_json(["foo"])
    assert found is True
    assert values == ["bar"]


def test_retrieve_from_json_not_found(tmp_path, monkeypatch):
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    with open(server_dir / "email.json", "w", encoding="utf8") as f:
        f.write("not json")
    monkeypatch.chdir(tmp_path)
    found, values = rfj.retrieve_from_json(["foo"])
    assert found is False
    assert values is None
