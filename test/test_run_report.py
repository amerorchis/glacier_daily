"""Tests for shared.run_report module."""

import json
import os
from unittest.mock import patch

from shared.run_context import start_run
from shared.run_report import (
    RunReport,
    build_report,
    upload_status_report,
)
from shared.timing import ModuleResult, get_timing


class TestRunReport:
    def test_to_json_valid(self):
        report = RunReport(run_id="abc123", run_type="email")
        parsed = json.loads(report.to_json())
        assert parsed["run_id"] == "abc123"
        assert parsed["run_type"] == "email"

    def test_to_dict(self):
        report = RunReport(run_id="abc123", overall_status="partial")
        d = report.to_dict()
        assert d["run_id"] == "abc123"
        assert d["overall_status"] == "partial"
        assert isinstance(d["modules"], dict)

    def test_default_status_is_success(self):
        report = RunReport()
        assert report.overall_status == "success"


class TestBuildReport:
    def test_build_with_run_context(self):
        run = start_run("email")
        report = build_report(environment="development")
        assert report.run_id == run.run_id
        assert report.run_type == "email"
        assert report.environment == "development"
        assert report.overall_status == "success"

    def test_build_without_run_context(self):
        report = build_report()
        assert report.run_id == "unknown"
        assert report.run_type == "unknown"

    def test_build_status_partial(self):
        start_run("web_update")
        timing = get_timing()
        timing.record(
            ModuleResult(name="weather", status="success", duration_seconds=1.0)
        )
        timing.record(
            ModuleResult(
                name="trails", status="error", duration_seconds=0.5, error="timeout"
            )
        )
        report = build_report()
        assert report.overall_status == "partial"
        assert len(report.errors) == 1
        assert "trails: timeout" in report.errors[0]

    def test_build_status_failure(self):
        start_run("email")
        timing = get_timing()
        timing.record(
            ModuleResult(
                name="weather", status="error", duration_seconds=1.0, error="down"
            )
        )
        timing.record(
            ModuleResult(
                name="trails", status="error", duration_seconds=0.5, error="timeout"
            )
        )
        report = build_report()
        assert report.overall_status == "failure"
        assert len(report.errors) == 2

    def test_build_includes_timing_summary(self):
        start_run("email")
        timing = get_timing()
        timing.record(
            ModuleResult(name="weather", status="success", duration_seconds=2.345)
        )
        report = build_report()
        assert "weather" in report.modules
        assert report.modules["weather"]["status"] == "success"
        assert report.modules["weather"]["duration_seconds"] == 2.35

    def test_build_report_run_type_web_update(self):
        start_run("web_update")
        report = build_report()
        assert report.run_type == "web_update"


class TestUploadStatusReport:
    def test_creates_status_file_and_uploads(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "server" / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        report = RunReport(
            run_id="abc123",
            run_type="email",
            end_time="2026-02-20T08:00:00",
            overall_status="success",
        )

        with patch("shared.run_report.upload_file") as mock_upload:
            upload_status_report(report)

        assert os.path.exists(status_file)
        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "abc123"
        # First call uploads status.json, second uploads status.html
        calls = mock_upload.call_args_list
        assert calls[0].args == ("api", "status.json", status_file)
        assert calls[1].args[:2] == ("api", "status.html")

    def test_appends_to_existing_history(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        # Seed with an existing run
        existing = {
            "runs": [
                {
                    "run_id": "old1",
                    "run_type": "web_update",
                    "end_time": "2026-02-19T12:00:00",
                }
            ]
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        report = RunReport(
            run_id="new1",
            run_type="email",
            end_time="2026-02-20T08:00:00",
        )

        with patch("shared.run_report.upload_file"):
            upload_status_report(report)

        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 2
        assert data["runs"][0]["run_id"] == "old1"
        assert data["runs"][1]["run_id"] == "new1"

    def test_trims_entries_older_than_history_days(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        # Seed with a very old run that should be trimmed
        existing = {
            "runs": [
                {
                    "run_id": "ancient",
                    "run_type": "email",
                    "end_time": "2020-01-01T08:00:00",
                }
            ]
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        report = RunReport(
            run_id="current",
            run_type="email",
            end_time="2026-02-20T08:00:00",
        )

        with patch("shared.run_report.upload_file"):
            upload_status_report(report)

        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        # Old entry trimmed, only current remains
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "current"

    def test_handles_corrupted_status_file(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        # Write corrupt JSON
        with open(status_file, "w", encoding="utf-8") as f:
            f.write("{bad json")

        report = RunReport(
            run_id="fresh", run_type="web_update", end_time="2026-02-20T10:00:00"
        )

        with patch("shared.run_report.upload_file"):
            upload_status_report(report)

        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "fresh"
