"""
Module for testing the Drip API functionality.
"""

import sys
import os

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from drip.subscriber_list import subscriber_list

def test_subscriber_list_not_empty():
    """Test that subscriber_list returns a non-empty list."""
    subscribers = subscriber_list()
    assert isinstance(subscribers, list), "subscriber_list() should return a list"
    assert len(subscribers) > 0, "subscriber_list() returned an empty list"

    invalid_emails = [email for email in subscribers if '@' not in email]
    assert not invalid_emails, f"The following subscribers are missing '@' symbol: {invalid_emails}"
