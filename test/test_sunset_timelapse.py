from datetime import datetime
from unittest.mock import patch

from sunset_timelapse.get_timelapse import (
    find_matching_sunset_thumbnail,
    process_sunset_video,
    select_sunset_video,
)

# Mock data for testing — the feed mixes sunrise and sunset entries
MOCK_TIMELAPSE_DATA = [
    {"date": "2025-08-20 21:19:06.770128"},
    {
        "id": "latest",
        "vid_src": "/daily/sunrise_vid/8_20_2025_sunrise_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=latest",
        "title": "Latest Sunrise Timelapse",
        "string": "Latest Sunrise",
    },
    {
        "id": "latest_sunset",
        "vid_src": "/daily/sunrise_vid/8_20_2025_sunset_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=latest_sunset",
        "title": "Latest Sunset Timelapse",
        "string": "Latest Sunset",
    },
    {
        "id": "8_20_2025_sunrise_timelapse",
        "vid_src": "/daily/sunrise_vid/8_20_2025_sunrise_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunrise_timelapse",
        "title": "8-20 Sunrise Timelapse",
        "string": "8-20 Sunrise",
    },
    {
        "id": "8_20_2025_sunset_timelapse",
        "vid_src": "/daily/sunrise_vid/8_20_2025_sunset_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunset_timelapse",
        "title": "8-20 Sunset Timelapse",
        "string": "8-20 Sunset",
    },
    {
        "id": "8_19_2025_sunset_timelapse",
        "vid_src": "/daily/sunrise_vid/8_19_2025_sunset_timelapse.mp4",
        "url": "https://glacier.org/webcam-timelapse/?type=daily&id=8_19_2025_sunset_timelapse",
        "title": "8-19 Sunset Timelapse",
        "string": "8-19 Sunset",
    },
]

MOCK_THUMBNAIL_DATA = [
    {"date": "2025-08-20 21:19:30.366413"},
    {"path": "/daily/sunrise_still/8_20_2025_sunrise.jpg"},
    {"path": "/daily/sunrise_still/8_20_2025_sunset.jpg"},
    {"path": "/daily/sunrise_still/8_19_2025_sunset.jpg"},
]


class TestSelectSunsetVideo:
    @patch(
        "sunset_timelapse.get_timelapse.now_mountain",
        return_value=datetime(2025, 8, 20),
    )
    def test_select_tonights_video(self, mock_now):
        """Test selecting tonight's video when available."""
        video_id, video_url, descriptor = select_sunset_video(MOCK_TIMELAPSE_DATA)

        assert video_id == "8_20_2025_sunset_timelapse"
        assert (
            video_url
            == "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunset_timelapse"
        )
        assert descriptor == "Tonight's"

    @patch(
        "sunset_timelapse.get_timelapse.now_mountain",
        return_value=datetime(2025, 8, 21),
    )
    def test_select_latest_sunset_fallback(self, mock_now):
        """Test falling back to latest_sunset when tonight's is not available."""
        video_id, video_url, descriptor = select_sunset_video(MOCK_TIMELAPSE_DATA)

        assert video_id == "8_20_2025"
        assert (
            video_url
            == "https://glacier.org/webcam-timelapse/?type=daily&id=latest_sunset"
        )
        assert descriptor == "Latest"

    def test_select_video_empty_data(self):
        """Test handling empty data."""
        result = select_sunset_video([])

        assert result == (None, None, None)

    @patch(
        "sunset_timelapse.get_timelapse.now_mountain",
        return_value=datetime(2025, 8, 21),
    )
    def test_select_video_no_sunset_entries(self, mock_now):
        """No arbitrary-entry fallback: sunrise-only feeds return nothing."""
        sunrise_only = [
            {"date": "2025-08-20 07:19:06.770128"},
            {
                "id": "8_20_2025_sunrise_timelapse",
                "vid_src": "/daily/sunrise_vid/8_20_2025_sunrise_timelapse.mp4",
                "url": "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunrise_timelapse",
            },
        ]

        result = select_sunset_video(sunrise_only)

        assert result == (None, None, None)


class TestFindMatchingSunsetThumbnail:
    def test_find_matching_thumbnail_success(self):
        """Test finding matching thumbnail for a sunset video."""
        result = find_matching_sunset_thumbnail(
            "8_20_2025_sunset_timelapse", MOCK_THUMBNAIL_DATA
        )

        assert result == "https://glacier.org/daily/sunrise_still/8_20_2025_sunset.jpg"

    def test_find_matching_thumbnail_date_only_id(self):
        """The latest_sunset fallback yields a bare date id — still matches."""
        result = find_matching_sunset_thumbnail("8_20_2025", MOCK_THUMBNAIL_DATA)

        assert result == "https://glacier.org/daily/sunrise_still/8_20_2025_sunset.jpg"

    def test_find_matching_thumbnail_does_not_match_sunrise(self):
        """A date with only a sunrise thumbnail must not match."""
        sunrise_only = [
            {"date": "2025-08-20 21:19:30.366413"},
            {"path": "/daily/sunrise_still/8_20_2025_sunrise.jpg"},
        ]

        result = find_matching_sunset_thumbnail(
            "8_20_2025_sunset_timelapse", sunrise_only
        )

        assert result is None

    def test_find_matching_thumbnail_no_match(self):
        """Test when no matching thumbnail is found."""
        result = find_matching_sunset_thumbnail(
            "8_22_2025_sunset_timelapse", MOCK_THUMBNAIL_DATA
        )

        assert result is None

    def test_find_matching_thumbnail_empty_data(self):
        """Test handling empty thumbnail data."""
        result = find_matching_sunset_thumbnail("8_20_2025_sunset_timelapse", [])

        assert result is None

    def test_find_matching_thumbnail_empty_video_id(self):
        """Test handling empty video ID."""
        result = find_matching_sunset_thumbnail("", MOCK_THUMBNAIL_DATA)

        assert result is None


class TestProcessSunsetVideo:
    @patch("sunset_timelapse.get_timelapse.fetch_glacier_data")
    @patch(
        "sunset_timelapse.get_timelapse.now_mountain",
        return_value=datetime(2025, 8, 20),
    )
    def test_process_sunset_video_success(self, mock_now, mock_fetch_data):
        """Test successful video processing end to end."""

        def fetch_side_effect(endpoint_type):
            if endpoint_type == "timelapse":
                return MOCK_TIMELAPSE_DATA
            if endpoint_type == "thumbnails":
                return MOCK_THUMBNAIL_DATA
            return []

        mock_fetch_data.side_effect = fetch_side_effect

        result = process_sunset_video()

        assert result == (
            "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunset_timelapse",
            "https://glacier.org/daily/sunrise_still/8_20_2025_sunset.jpg",
            "Tonight's",
        )

    @patch("sunset_timelapse.get_timelapse.fetch_glacier_data")
    def test_process_sunset_video_fetch_failure(self, mock_fetch_data):
        """Test handling when data fetching fails."""

        def fetch_side_effect(endpoint_type):
            if endpoint_type == "timelapse":
                return []
            if endpoint_type == "thumbnails":
                return MOCK_THUMBNAIL_DATA
            return []

        mock_fetch_data.side_effect = fetch_side_effect

        result = process_sunset_video()

        assert result == ("", "", "")

    @patch("sunset_timelapse.get_timelapse.fetch_glacier_data")
    @patch("sunset_timelapse.get_timelapse.select_sunset_video")
    def test_process_sunset_video_no_suitable_video(
        self, mock_select_video, mock_fetch_data
    ):
        """Test handling when no suitable video is found."""

        def fetch_side_effect(endpoint_type):
            if endpoint_type == "timelapse":
                return MOCK_TIMELAPSE_DATA
            if endpoint_type == "thumbnails":
                return MOCK_THUMBNAIL_DATA
            return []

        mock_fetch_data.side_effect = fetch_side_effect
        mock_select_video.return_value = (None, None, None)

        result = process_sunset_video()

        assert result == ("", "", "")

    @patch("sunset_timelapse.get_timelapse.fetch_glacier_data")
    @patch("sunset_timelapse.get_timelapse.select_sunset_video")
    @patch("sunset_timelapse.get_timelapse.find_matching_sunset_thumbnail")
    def test_process_sunset_video_no_matching_thumbnail(
        self,
        mock_find_thumbnail,
        mock_select_video,
        mock_fetch_data,
    ):
        """Test handling when no matching thumbnail is found."""

        def fetch_side_effect(endpoint_type):
            if endpoint_type == "timelapse":
                return MOCK_TIMELAPSE_DATA
            if endpoint_type == "thumbnails":
                return MOCK_THUMBNAIL_DATA
            return []

        mock_fetch_data.side_effect = fetch_side_effect
        mock_select_video.return_value = (
            "8_20_2025_sunset_timelapse",
            "https://glacier.org/webcam-timelapse/?type=daily&id=8_20_2025_sunset_timelapse",
            "Tonight's",
        )
        mock_find_thumbnail.return_value = None

        result = process_sunset_video()

        assert result == ("", "", "")

    @patch("sunset_timelapse.get_timelapse.fetch_glacier_data")
    def test_process_sunset_video_exception_handling(self, mock_fetch_data):
        """Test handling unexpected exceptions."""
        mock_fetch_data.side_effect = Exception("Unexpected error")

        result = process_sunset_video()

        assert result == ("", "", "")
