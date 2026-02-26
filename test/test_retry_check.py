import json
import os

import pytest

import retry_check


@pytest.fixture(autouse=True)
def _use_tmp_paths(tmp_path, monkeypatch):
    """Point status and lock files at a temp directory."""
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    monkeypatch.setattr(retry_check, "LOCK_FILE", tmp_path / "test.lock")
    monkeypatch.setattr(retry_check, "PROJECT_DIR", tmp_path)


def _write_status(tmp_path, runs):
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps({"runs": runs}))


def _today():
    return retry_check.now_mountain().strftime("%Y-%m-%d")


# ============================================================================
# has_successful_email_today tests
# ============================================================================


def test_successful_email_today_returns_true(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "email",
                "overall_status": "success",
                "start_time": f"{_today()}T07:30:00",
            }
        ],
    )
    assert retry_check.has_successful_email_today() is True


def test_wrong_run_type_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "web_update",
                "overall_status": "success",
                "start_time": f"{_today()}T07:30:00",
            }
        ],
    )
    assert retry_check.has_successful_email_today() is False


def test_wrong_status_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "email",
                "overall_status": "failure",
                "start_time": f"{_today()}T07:30:00",
            }
        ],
    )
    assert retry_check.has_successful_email_today() is False


def test_wrong_date_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "email",
                "overall_status": "success",
                "start_time": "2020-01-01T07:30:00",
            }
        ],
    )
    assert retry_check.has_successful_email_today() is False


def test_empty_runs_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(tmp_path, [])
    assert retry_check.has_successful_email_today() is False


def test_no_status_file_returns_false():
    assert retry_check.has_successful_email_today() is False


def test_corrupt_status_file_returns_false(tmp_path, monkeypatch):
    status_file = tmp_path / "status.json"
    monkeypatch.setattr(retry_check, "STATUS_FILE", status_file)
    status_file.write_text("not valid json{{{")
    assert retry_check.has_successful_email_today() is False


# ============================================================================
# is_locked tests
# ============================================================================


def test_no_lock_file_returns_false():
    assert retry_check.is_locked() is False


def test_lock_with_alive_pid_returns_true(tmp_path, monkeypatch):
    lock_file = tmp_path / "test.lock"
    monkeypatch.setattr(retry_check, "LOCK_FILE", lock_file)
    lock_file.write_text(str(os.getpid()))  # Our own PID is definitely alive
    assert retry_check.is_locked() is True


def test_lock_with_dead_pid_returns_false(tmp_path, monkeypatch):
    lock_file = tmp_path / "test.lock"
    monkeypatch.setattr(retry_check, "LOCK_FILE", lock_file)
    lock_file.write_text("99999999")  # Very unlikely to be a real PID
    assert retry_check.is_locked() is False


def test_lock_with_invalid_content_returns_false(tmp_path, monkeypatch):
    lock_file = tmp_path / "test.lock"
    monkeypatch.setattr(retry_check, "LOCK_FILE", lock_file)
    lock_file.write_text("not-a-pid")
    assert retry_check.is_locked() is False


# ============================================================================
# retry() integration tests
# ============================================================================


def test_retry_no_action_when_successful(tmp_path, monkeypatch):
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "email",
                "overall_status": "success",
                "start_time": f"{_today()}T07:30:00",
            }
        ],
    )
    assert retry_check.retry() == 0


def test_retry_exits_3_when_locked(tmp_path, monkeypatch):
    lock_file = tmp_path / "test.lock"
    monkeypatch.setattr(retry_check, "LOCK_FILE", lock_file)
    lock_file.write_text(str(os.getpid()))
    assert retry_check.retry() == 3


def test_retry_dry_run_does_not_launch(tmp_path):
    # No status file, no lock → would normally launch
    assert retry_check.retry(dry_run=True) == 0


def test_retry_launches_subprocess(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("retry_check.subprocess.run", mock_run)
    result = retry_check.retry()
    assert result == 0
    assert len(calls) == 1
    assert "main.py" in calls[0][-1]


def test_retry_passes_tag_to_subprocess(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("retry_check.subprocess.run", mock_run)
    result = retry_check.retry(tag="Test Glacier Daily Update")
    assert result == 0
    assert "--tag" in calls[0]
    assert "Test Glacier Daily Update" in calls[0]


def test_retry_with_tag_still_checks_status(tmp_path, monkeypatch):
    """Even with --tag, should not retry if today already has a successful run."""
    monkeypatch.setattr(retry_check, "STATUS_FILE", tmp_path / "status.json")
    _write_status(
        tmp_path,
        [
            {
                "run_type": "email",
                "overall_status": "success",
                "start_time": f"{_today()}T07:30:00",
            }
        ],
    )
    result = retry_check.retry(tag="Test Glacier Daily Update")
    assert result == 0  # No-op, not a subprocess launch
