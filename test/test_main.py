import builtins
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

import main


def test_main_runs_all_steps(monkeypatch):
    calls = []
    # Patch sleep_to_sunrise, get_subs, serve_api, sleep, bulk_workflow_trigger
    monkeypatch.setattr(
        main, "sleep_to_sunrise", lambda: calls.append("sleep_to_sunrise")
    )
    monkeypatch.setattr(
        main,
        "get_subs",
        lambda tag: calls.append(f"get_subs:{tag}") or ["test@example.com"],
    )
    monkeypatch.setattr(main, "serve_api", lambda: calls.append("serve_api"))
    monkeypatch.setattr(main, "sleep", lambda x: calls.append(f"sleep:{x}"))
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: calls.append(f"bulk_workflow_trigger:{subs}"),
    )

    monkeypatch.setattr(
        main,
        "record_drip_event",
        lambda email, event="Glacier Daily Update trigger": calls.append(
            f"record_drip_event:{email}:{event}"
        ),
    )
    main.main(tag="TestTag", test=True)
    # Should call all steps in order
    assert calls == [
        "sleep_to_sunrise",
        "get_subs:TestTag",
        "serve_api",
        "record_drip_event:andrew@glacier.org:Glacier Daily Update trigger",
        "sleep:0",
        "bulk_workflow_trigger:['test@example.com']",
    ]


def test_main_test_flag_skips_sleep(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "sleep_to_sunrise", lambda: calls.append("sleep_to_sunrise")
    )
    monkeypatch.setattr(
        main,
        "get_subs",
        lambda tag: calls.append(f"get_subs:{tag}") or ["test@example.com"],
    )
    monkeypatch.setattr(main, "serve_api", lambda: calls.append("serve_api"))
    monkeypatch.setattr(main, "sleep", lambda x: calls.append(f"sleep:{x}"))
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: calls.append(f"bulk_workflow_trigger:{subs}"),
    )

    monkeypatch.setattr(
        main,
        "record_drip_event",
        lambda email, event="Glacier Daily Update trigger": calls.append(
            f"record_drip_event:{email}:{event}"
        ),
    )
    main.main(test=True)
    assert "sleep:0" in calls


def test_main_default_tag(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main, "sleep_to_sunrise", lambda: calls.append("sleep_to_sunrise")
    )
    monkeypatch.setattr(
        main,
        "get_subs",
        lambda tag: calls.append(f"get_subs:{tag}") or ["test@example.com"],
    )
    monkeypatch.setattr(main, "serve_api", lambda: calls.append("serve_api"))
    monkeypatch.setattr(main, "sleep", lambda x: calls.append(f"sleep:{x}"))
    monkeypatch.setattr(
        main,
        "bulk_workflow_trigger",
        lambda subs: calls.append(f"bulk_workflow_trigger:{subs}"),
    )

    monkeypatch.setattr(
        main,
        "record_drip_event",
        lambda email, event="Glacier Daily Update trigger": calls.append(
            f"record_drip_event:{email}:{event}"
        ),
    )
    main.main()
    assert any("get_subs:Glacier Daily Update" in c for c in calls)
