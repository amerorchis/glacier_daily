import main


def _patch_main(monkeypatch, calls):
    """Apply standard monkeypatches for main module tests."""
    monkeypatch.setattr(main, "setup_logging", lambda: None)
    monkeypatch.setattr(main, "validate_config", lambda: None)
    monkeypatch.setattr(main, "acquire_lock", lambda: 999)
    monkeypatch.setattr(main, "release_lock", lambda fd: None)
    monkeypatch.setattr(
        main, "sleep_to_sunrise", lambda: calls.append("sleep_to_sunrise")
    )
    monkeypatch.setattr(
        main,
        "get_subs",
        lambda tag: calls.append(f"get_subs:{tag}") or ["test@example.com"],
    )
    monkeypatch.setattr(main, "serve_api", lambda **kw: calls.append("serve_api"))
    monkeypatch.setattr(main, "sleep", lambda x: calls.append(f"sleep:{x}"))
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: calls.append(f"bulk_workflow_trigger:{subs}"),
    )
    monkeypatch.setattr(main, "check_canary_delivery", lambda: None)


def test_main_runs_all_steps(monkeypatch):
    calls = []
    _patch_main(monkeypatch, calls)

    main.main(tag="TestTag", test=True)
    assert calls == [
        "sleep_to_sunrise",
        "get_subs:TestTag",
        "serve_api",
        "sleep:0",
        "bulk_workflow_trigger:['test@example.com']",
    ]


def test_main_test_flag_skips_sleep(monkeypatch):
    calls = []
    _patch_main(monkeypatch, calls)

    main.main(test=True)
    assert "sleep:0" in calls


def test_main_default_tag(monkeypatch):
    calls = []
    _patch_main(monkeypatch, calls)

    main.main()
    assert any("get_subs:Glacier Daily Update" in c for c in calls)


def test_main_runs_canary_when_emails_sent(monkeypatch):
    from drip.canary_check import CanaryResult
    from drip.drip_actions import BatchResult

    calls = []
    _patch_main(monkeypatch, calls)
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: BatchResult(sent=1, failed=0),
    )
    monkeypatch.setattr(
        main,
        "check_canary_delivery",
        lambda: calls.append("canary") or CanaryResult(verified=True, message="ok"),
    )

    main.main(test=True)
    assert "canary" in calls


def test_main_skips_canary_when_no_emails_sent(monkeypatch):
    from drip.drip_actions import BatchResult

    calls = []
    _patch_main(monkeypatch, calls)
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: BatchResult(sent=0, failed=0),
    )
    monkeypatch.setattr(
        main,
        "check_canary_delivery",
        lambda: calls.append("canary_should_not_run"),
    )

    main.main(test=True)
    assert "canary_should_not_run" not in calls


def test_main_exits_when_locked(monkeypatch):
    calls = []
    _patch_main(monkeypatch, calls)
    monkeypatch.setattr(main, "acquire_lock", lambda: None)

    main.main(test=True)
    assert "sleep_to_sunrise" not in calls


def test_main_catches_serve_api_exception(monkeypatch):
    """When serve_api raises, main() logs the error instead of propagating."""
    calls = []
    _patch_main(monkeypatch, calls)

    def raise_on_serve(**kw):
        raise TypeError("can't compare offset-naive and offset-aware datetimes")

    monkeypatch.setattr(main, "serve_api", raise_on_serve)

    # Should not raise — the exception is caught and logged
    main.main(test=True)
    # Email sending should not have been attempted
    assert not any("bulk_workflow_trigger" in c for c in calls)


def test_main_catches_email_delivery_exception(monkeypatch):
    """When bulk_workflow_trigger raises, main() logs the error instead of propagating."""
    calls = []
    _patch_main(monkeypatch, calls)

    def raise_on_trigger(subs):
        raise RuntimeError("Drip API exploded")

    monkeypatch.setattr(main, "bulk_workflow_trigger", raise_on_trigger)

    # Should not raise — the exception is caught and logged
    main.main(test=True)
    # serve_api should have completed
    assert "serve_api" in calls


def test_main_fails_when_no_subscribers(monkeypatch):
    """When get_subs returns empty list, run is marked as failure (not success)."""
    calls = []
    _patch_main(monkeypatch, calls)
    monkeypatch.setattr(main, "get_subs", lambda tag: [])

    # Should not raise — the exception is caught internally
    main.main(test=True)
    # Data generation and email sending should not have been attempted
    assert "serve_api" not in calls
    assert not any("bulk_workflow_trigger" in c for c in calls)
