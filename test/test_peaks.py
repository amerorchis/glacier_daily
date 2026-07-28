import csv
import io
import json
import re
from datetime import date, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from PIL import Image

from peak.peak import (
    PEAKS_CSV,
    SCRIPT_DIR,
    _get_peak_summary,
    peak,
    select_peak,
)
from peak.sat import peak_sat, prepare_peak_upload, upload_peak


@pytest.fixture
def mock_env_vars():
    """Mock Mapbox environment variables"""
    with patch.dict(
        "os.environ",
        {
            "MAPBOX_TOKEN": "test_token",
            "MAPBOX_ACCOUNT": "test_account",
            "MAPBOX_STYLE": "test_style",
        },
    ):
        yield


@pytest.fixture
def sample_peak_data():
    """Sample peak data for testing"""
    return {
        "name": "Test Peak",
        "elevation": "8000",
        "lat": "48.99815",
        "lon": "-114.21147",
    }


@pytest.fixture
def sample_image():
    """Create a sample image buffer"""
    img = Image.new("RGB", (100, 100), color="red")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="JPEG")
    img_buffer.seek(0)
    return img_buffer


def test_peak_selection(mock_env_vars):
    """Test peak selection returns a correctly formatted result"""
    result = peak(test=True)

    peak_name, peak_img, peak_map = result
    assert isinstance(peak_name, str)
    assert "ft." in peak_name
    assert peak_map.startswith("https://www.google.com/maps/place/")
    assert peak_img is None  # Should be None in test mode


def test_peak_selection_uses_todays_date(mock_env_vars):
    """Test that the peak shown matches the one selected for today's date"""
    with open(PEAKS_CSV, encoding="utf-8") as f:
        peaks = list(csv.DictReader(f))

    expected = select_peak(peaks, date.today())
    peak_name, _, _ = peak(test=True)

    assert peak_name.startswith(f"{expected['name']} - {expected['elevation']} ft.")


def test_peak_sat_image_generation(mock_env_vars, sample_peak_data):
    """Test satellite image generation for a peak"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test_image_content"

    with (
        patch("requests.get", return_value=mock_response),
        patch("PIL.Image.open") as mock_open,
        patch("peak.sat.upload_peak", return_value="https://example.com/peak.jpg"),
    ):
        result = peak_sat(sample_peak_data)

        # Verify Mapbox API was called correctly
        requests.get.assert_called_once()
        assert "api.mapbox.com" in requests.get.call_args[0][0]
        assert "test_token" in requests.get.call_args[0][0]

        # Verify image was processed and uploaded
        mock_open.assert_called_once()
        assert result == "https://example.com/peak.jpg"


def test_peak_sat_api_error(mock_env_vars, sample_peak_data):
    """Test handling of Mapbox API errors"""
    with (
        patch("requests.get", side_effect=requests.RequestException("API Error")),
        patch("shared.retry.sleep"),
    ):
        result = peak_sat(sample_peak_data)
        assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_peak_sat_image_processing_error(mock_env_vars, sample_peak_data):
    """Test handling of image processing errors"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"invalid_image_data"

    with patch("requests.get", return_value=mock_response):
        result = peak_sat(sample_peak_data)
        assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_upload_peak(mock_env_vars):
    """Test peak image upload functionality"""
    from shared.datetime_utils import now_mountain

    today = now_mountain()
    expected_filename = f"{today.month}_{today.day}_{today.year}_peak.jpg"

    mock_ftp = MagicMock()
    mock_ftp.__enter__ = MagicMock(return_value=mock_ftp)
    mock_ftp.__exit__ = MagicMock(return_value=False)
    mock_ftp.upload.return_value = ("https://example.com/peak.jpg", [])

    with patch("peak.sat.FTPSession", return_value=mock_ftp):
        result = upload_peak()

        mock_ftp.upload.assert_called_once_with(
            "peak", expected_filename, "email_images/today/peak.jpg"
        )
        assert result == "https://example.com/peak.jpg"


def test_peak_sat_skip_upload(mock_env_vars, sample_peak_data):
    """Test peak_sat with skip_upload=True returns None on success."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"test_image_content"

    with (
        patch("requests.get", return_value=mock_response),
        patch("PIL.Image.open") as mock_open,
    ):
        result = peak_sat(sample_peak_data, skip_upload=True)
        assert result is None
        mock_open.return_value.save.assert_called_once()


def test_prepare_peak_upload():
    """Test prepare_peak_upload returns correct tuple."""
    directory, filename, local_path = prepare_peak_upload()
    assert directory == "peak"
    assert filename.endswith("_peak.jpg")
    assert local_path == "email_images/today/peak.jpg"


def test_peak_with_invalid_coordinates(mock_env_vars):
    """Test handling of invalid peak coordinates"""
    invalid_peak = {
        "name": "Invalid Peak",
        "elevation": "8000",
        "lat": "invalid",
        "lon": "invalid",
    }

    with patch("shared.retry.sleep"):
        result = peak_sat(invalid_peak)
    assert result == "https://glacier.org/daily/summer/peak.jpg"


def test_peak_csv_read():
    """Test reading of peaks from CSV"""
    result = peak(test=True)

    # Verify basic peak data format
    peak_name, _, peak_map = result
    assert " - " in peak_name  # Should contain name and elevation
    assert "ft." in peak_name
    assert "@" in peak_map  # Should contain coordinates


class TestSelectPeak:
    """Tests for the date-seeded peak rotation"""

    @pytest.fixture
    def peaks(self):
        return [{"name": f"Peak {i}", "elevation": str(i)} for i in range(10)]

    def test_deterministic_for_a_given_day(self, peaks):
        """The same date always yields the same peak"""
        day = date(2026, 7, 27)
        assert select_peak(peaks, day) == select_peak(peaks, day)

    def test_every_peak_used_exactly_once_per_cycle(self, peaks):
        """A full cycle of len(peaks) days covers the whole list with no repeats"""
        start = date(2026, 1, 1)
        picked = [
            select_peak(peaks, start + timedelta(days=i)) for i in range(len(peaks))
        ]

        names = [p["name"] for p in picked]
        assert sorted(names) == sorted(p["name"] for p in peaks)
        assert len(set(names)) == len(peaks)

    def test_consecutive_cycles_use_different_orders(self, peaks):
        """Each cycle reshuffles rather than repeating the same sequence"""
        start = date(2026, 1, 1)
        n = len(peaks)
        first = [
            select_peak(peaks, start + timedelta(days=i))["name"] for i in range(n)
        ]
        second = [
            select_peak(peaks, start + timedelta(days=n + i))["name"] for i in range(n)
        ]

        assert sorted(first) == sorted(second)  # same peaks
        assert first != second  # different order

    def test_handles_dates_before_the_epoch(self, peaks):
        """Dates before the cycle epoch still index inside the list"""
        from peak.peak import PEAK_CYCLE_EPOCH

        for i in range(1, 40):
            selected = select_peak(peaks, PEAK_CYCLE_EPOCH - timedelta(days=i))
            assert selected in peaks

    def test_real_peak_list_has_no_duplicates(self):
        """The shipped CSV should not list the same peak twice"""
        with open(PEAKS_CSV, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        names = [r["name"] for r in rows]
        assert len(names) == len(set(names)), "duplicate peak names in PeaksCSV.csv"

    def test_works_from_any_working_directory(
        self, mock_env_vars, tmp_path, monkeypatch
    ):
        """Data files are resolved relative to the module, not the cwd"""
        monkeypatch.chdir(tmp_path)
        peak_name, _, _ = peak(test=True)
        assert "ft." in peak_name


class TestPeakDataFiles:
    """Consistency checks across the shipped peak data files"""

    @pytest.fixture
    def rows(self):
        with open(PEAKS_CSV, encoding="utf-8") as f:
            return list(csv.DictReader(f))

    @pytest.fixture
    def wiki(self):
        with open(SCRIPT_DIR / "peaks_wikipedia.json", encoding="utf-8") as f:
            return json.load(f)

    def test_csv_and_wikipedia_json_agree(self, rows, wiki):
        """
        The JSON must carry the same names and coords as the CSV, in order.

        _get_peak_summary matches on exact name plus coordinates, so a name that
        drifts between the two files silently drops that peak's summary.
        """
        csv_keys = [(r["name"], round(float(r["lat"]), 5)) for r in rows]
        json_keys = [(p["name"], round(p["lat"], 5)) for p in wiki["peaks"]]
        assert csv_keys == json_keys

    def test_every_summary_is_reachable(self, wiki):
        """Each summary in the JSON can actually be looked up by peak.py"""
        for p in wiki["peaks"]:
            if p.get("summary"):
                assert _get_peak_summary(p["name"], p["lat"], p["lon"]) == p["summary"]

    def test_no_wikipedia_csv_matches_has_article_flags(self, wiki):
        """peaks_no_wikipedia.csv lists exactly the peaks with no article"""
        with open(SCRIPT_DIR / "peaks_no_wikipedia.csv", encoding="utf-8") as f:
            listed = {r["name"] for r in csv.DictReader(f)}

        assert listed == {p["name"] for p in wiki["peaks"] if not p["has_article"]}

    def test_metadata_counts_are_current(self, wiki):
        """The metadata block reflects the actual contents"""
        peaks = wiki["peaks"]
        with_article = sum(1 for p in peaks if p["has_article"])
        assert wiki["metadata"]["total_peaks"] == len(peaks)
        assert wiki["metadata"]["peaks_with_articles"] == with_article
        assert wiki["metadata"]["peaks_without_articles"] == len(peaks) - with_article

    def test_no_disambiguation_pages_stored(self, wiki):
        """Stored article text should be a real article, not a disambiguation page"""
        pattern = re.compile(r"\b(may refer to|can refer to|could be)\b", re.IGNORECASE)
        bad = [
            p["name"]
            for p in wiki["peaks"]
            if pattern.search((p["wikipedia_text"] or "")[:200])
        ]
        assert not bad, f"disambiguation pages stored for: {bad}"

    def test_article_links_are_consistent_with_flags(self, wiki):
        """has_article must agree with whether a url and text are present"""
        for p in wiki["peaks"]:
            if p["has_article"]:
                assert p["wikipedia_url"] and p["wikipedia_text"], p["name"]
            else:
                assert p["wikipedia_url"] is None and p["wikipedia_text"] is None, p[
                    "name"
                ]


class TestGetPeakSummary:
    """Tests for the _get_peak_summary function"""

    def test_returns_none_when_json_missing(self, tmp_path):
        """Test that None is returned when JSON file doesn't exist"""
        with patch("peak.peak.WIKIPEDIA_JSON", tmp_path / "nonexistent.json"):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result is None

    def test_returns_summary_when_peak_found(self, tmp_path):
        """Test that summary is returned when peak matches"""
        json_file = tmp_path / "peaks_wikipedia.json"
        json_file.write_text(
            '{"peaks": [{"name": "Test Peak", "lat": 48.0, "lon": -113.0, '
            '"summary": "A test summary."}]}'
        )

        with patch("peak.peak.WIKIPEDIA_JSON", json_file):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result == "A test summary."

    def test_returns_none_when_peak_has_no_summary(self, tmp_path):
        """Test that None is returned when peak exists but has no summary"""
        json_file = tmp_path / "peaks_wikipedia.json"
        json_file.write_text(
            '{"peaks": [{"name": "Test Peak", "lat": 48.0, "lon": -113.0}]}'
        )

        with patch("peak.peak.WIKIPEDIA_JSON", json_file):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result is None

    def test_returns_none_when_peak_not_found(self, tmp_path):
        """Test that None is returned when no matching peak exists"""
        json_file = tmp_path / "peaks_wikipedia.json"
        json_file.write_text(
            '{"peaks": [{"name": "Other Peak", "lat": 49.0, "lon": -114.0, '
            '"summary": "Different peak."}]}'
        )

        with patch("peak.peak.WIKIPEDIA_JSON", json_file):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result is None

    def test_matches_by_coordinates_within_tolerance(self, tmp_path):
        """Test that peaks match within coordinate tolerance (0.001)"""
        json_file = tmp_path / "peaks_wikipedia.json"
        json_file.write_text(
            '{"peaks": [{"name": "Test Peak", "lat": 48.0005, "lon": -113.0005, '
            '"summary": "Matched within tolerance."}]}'
        )

        with patch("peak.peak.WIKIPEDIA_JSON", json_file):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result == "Matched within tolerance."

    def test_no_match_when_coordinates_outside_tolerance(self, tmp_path):
        """Test that peaks don't match when coords are outside tolerance"""
        json_file = tmp_path / "peaks_wikipedia.json"
        json_file.write_text(
            '{"peaks": [{"name": "Test Peak", "lat": 48.01, "lon": -113.01, '
            '"summary": "Should not match."}]}'
        )

        with patch("peak.peak.WIKIPEDIA_JSON", json_file):
            result = _get_peak_summary("Test Peak", 48.0, -113.0)
            assert result is None
