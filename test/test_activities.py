import sys
import os
from datetime import datetime

if sys.path[0] == os.path.dirname(os.path.abspath(__file__)):
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from activities.events import events_today

def test_activity_retrieval():
    """Test that events are retrieved and formatted for a known day."""
    with open('test/files/events.txt', 'r', encoding='utf8') as f:
        actual = f.read()
    assert events_today('2024-07-01') == actual

def test_no_activities_no_message():
    assert events_today(f'{datetime.now().year}-01-08') == ""

def test_no_activities_season_concluded():
    print(events_today(f'{datetime.now().year}-12-05'))
    assert events_today(f'{datetime.now().year}-12-05') == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs have concluded for the season.</p>'

def test_no_activities_season_not_started():
    assert events_today(f'{datetime.now().year}-04-05') == '<p style="margin:0 0 25px; font-size:12px; line-height:18px; color:#333333;">Ranger programs not started for the season.</p>'
