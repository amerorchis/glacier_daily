"""Tests for shared.run_report module."""

import json
import logging
import os
from datetime import timedelta

from shared.datetime_utils import now_mountain
from shared.logging_config import get_logger, setup_logging
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

    def test_build_status_partial_on_warnings(self):
        """Warnings (no errors) -> overall_status is 'partial'."""
        start_run("email")
        timing = get_timing()
        timing.record(
            ModuleResult(name="weather", status="success", duration_seconds=1.0)
        )
        timing.record(
            ModuleResult(
                name="sunrise",
                status="warning",
                duration_seconds=0.5,
                error="Unexpected error in process_video: codec error",
            )
        )
        report = build_report()
        assert report.overall_status == "partial"
        assert any("sunrise (warning)" in e for e in report.errors)

    def test_build_status_errors_and_warnings(self):
        """Mix of errors and warnings -> 'partial', both in errors list."""
        start_run("email")
        timing = get_timing()
        timing.record(
            ModuleResult(
                name="weather",
                status="error",
                duration_seconds=1.0,
                error="timeout",
            )
        )
        timing.record(
            ModuleResult(
                name="sunrise",
                status="warning",
                duration_seconds=0.5,
                error="no video",
            )
        )
        timing.record(
            ModuleResult(name="roads", status="success", duration_seconds=0.3)
        )
        report = build_report()
        assert report.overall_status == "partial"
        assert len(report.errors) == 2

    def test_build_status_all_warnings_not_failure(self):
        """All modules warned but none errored -> 'partial', not 'failure'."""
        start_run("email")
        timing = get_timing()
        timing.record(
            ModuleResult(
                name="weather",
                status="warning",
                duration_seconds=1.0,
                error="aqi failed",
            )
        )
        timing.record(
            ModuleResult(
                name="sunrise",
                status="warning",
                duration_seconds=0.5,
                error="no video",
            )
        )
        report = build_report()
        assert report.overall_status == "partial"

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


class TestBuildReportLogCapture:
    """Tests for log_lines integration in build_report."""

    @staticmethod
    def _setup_logging(monkeypatch):
        """Helper to set up logging with capture."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        root = logging.getLogger()
        root.handlers.clear()
        setup_logging()

    def test_build_report_includes_log_lines(self, monkeypatch):
        self._setup_logging(monkeypatch)
        start_run("email")
        logger = get_logger("test.report")
        logger.info("hello from test")
        report = build_report(environment="development")
        assert len(report.log_lines) >= 1
        assert any("hello from test" in line for line in report.log_lines)

    def test_build_report_empty_without_capture(self):
        start_run("email")
        report = build_report()
        assert report.log_lines == []

    def test_log_lines_serialized_in_json(self, monkeypatch):
        self._setup_logging(monkeypatch)
        start_run("email")
        get_logger("test.json").info("serialize me")
        report = build_report()
        parsed = json.loads(report.to_json())
        assert "log_lines" in parsed
        assert isinstance(parsed["log_lines"], list)
        assert any("serialize me" in line for line in parsed["log_lines"])


class TestFinalizeStatus:
    def test_no_delivery_data(self):
        report = RunReport(overall_status="success")
        report.finalize_status()
        assert report.overall_status == "success"

    def test_all_sent(self):
        report = RunReport(overall_status="success")
        report.email_delivery = {"sent": 100, "failed": 0}
        report.finalize_status()
        assert report.overall_status == "success"

    def test_some_failed_escalates_to_partial(self):
        report = RunReport(overall_status="success")
        report.email_delivery = {"sent": 90, "failed": 10}
        report.finalize_status()
        assert report.overall_status == "partial"

    def test_all_failed_escalates_to_failure(self):
        report = RunReport(overall_status="success")
        report.email_delivery = {"sent": 0, "failed": 100}
        report.finalize_status()
        assert report.overall_status == "failure"

    def test_partial_stays_partial_with_delivery_failures(self):
        report = RunReport(overall_status="partial")
        report.email_delivery = {"sent": 90, "failed": 10}
        report.finalize_status()
        assert report.overall_status == "partial"

    def test_failure_stays_failure(self):
        report = RunReport(overall_status="failure")
        report.email_delivery = {"sent": 100, "failed": 0}
        report.finalize_status()
        assert report.overall_status == "failure"

    def test_canary_failure_adds_error(self):
        report = RunReport(overall_status="success")
        report.email_delivery = {
            "sent": 100,
            "failed": 0,
            "canary_verified": False,
            "canary_message": "not received after 6 attempts",
        }
        report.finalize_status()
        # Status stays success (canary is informational)
        assert report.overall_status == "success"
        assert any("canary" in e for e in report.errors)

    def test_canary_success_no_error(self):
        report = RunReport(overall_status="success")
        report.email_delivery = {
            "sent": 100,
            "failed": 0,
            "canary_verified": True,
        }
        report.finalize_status()
        assert report.overall_status == "success"
        assert len(report.errors) == 0


class TestUploadStatusReport:
    def test_creates_status_file(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "server" / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        report = RunReport(
            run_id="abc123",
            run_type="email",
            end_time=now_mountain().isoformat(),
            overall_status="success",
        )

        upload_status_report(report)

        assert os.path.exists(status_file)
        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "abc123"

    def test_appends_to_existing_history(self, tmp_path, monkeypatch):
        status_file = str(tmp_path / "status.json")
        monkeypatch.setattr("shared.run_report.STATUS_FILE", status_file)

        # Seed with an existing run (use recent dates relative to now)
        recent = now_mountain().replace(hour=12, minute=0, second=0, microsecond=0)
        yesterday = (recent - timedelta(days=1)).isoformat()
        today = recent.isoformat()

        existing = {
            "runs": [
                {
                    "run_id": "old1",
                    "run_type": "web_update",
                    "end_time": yesterday,
                }
            ]
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        report = RunReport(
            run_id="new1",
            run_type="email",
            end_time=today,
        )

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
            end_time=now_mountain().isoformat(),
        )

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
            run_id="fresh", run_type="web_update", end_time=now_mountain().isoformat()
        )

        upload_status_report(report)

        with open(status_file, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["runs"]) == 1
        assert data["runs"][0]["run_id"] == "fresh"
