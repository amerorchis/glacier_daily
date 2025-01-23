"""
Test module for season determination functionality.
"""

import sys
import os
from datetime import datetime
import pytest

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pragma: no cover

from weather.season import get_season


@pytest.mark.parametrize(
    "test_date, expected_season",
    [
        # Test each season
        (datetime(2024, 1, 1), "winter"),
        (datetime(2024, 4, 1), "spring"),
        (datetime(2024, 7, 1), "summer"),
        (datetime(2024, 10, 1), "fall"),
        # Test boundary conditions
        (datetime(2024, 3, 31), "winter"),
        (datetime(2024, 4, 1), "spring"),
        (datetime(2024, 6, 30), "spring"),
        (datetime(2024, 7, 1), "summer"),
        (datetime(2024, 9, 30), "summer"),
        (datetime(2024, 10, 1), "fall"),
        (datetime(2024, 11, 30), "fall"),
        (datetime(2024, 12, 1), "winter"),
        # Test middle of seasons
        (datetime(2024, 1, 15), "winter"),
        (datetime(2024, 5, 15), "spring"),
        (datetime(2024, 8, 15), "summer"),
        (datetime(2024, 10, 15), "fall"),
    ],
)
def test_get_season_with_date(test_date, expected_season):
    assert get_season(test_date) == expected_season


def test_get_season_current_date():
    """Test that getting season for current date doesn't raise an error"""
    result = get_season()
    assert result in ["winter", "spring", "summer", "fall"]
