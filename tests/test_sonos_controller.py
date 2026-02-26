import pytest
from unittest.mock import patch, MagicMock, call
from apple_music import build_track_uri, build_track_metadata


SAMPLE_TRACKS = [
    {
        "track_id": 1440904001,
        "name": "Women",
        "track_number": 1,
        "artist": "Def Leppard",
        "album": "Hysteria",
        "artwork_url": "https://example.com/600x600bb.jpg",
    },
    {
        "track_id": 1440904002,
        "name": "Rocket",
        "track_number": 2,
        "artist": "Def Leppard",
        "album": "Hysteria",
        "artwork_url": "https://example.com/600x600bb.jpg",
    },
]


class TestPlayAlbum:
    def test_clears_queue_first(self, mock_speaker):
        from sonos_controller import play_album
        play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        mock_speaker.clear_queue.assert_called_once()

    def test_adds_all_tracks(self, mock_speaker):
        from sonos_controller import play_album
        play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        assert mock_speaker.add_uri_to_queue.call_count == 2

    def test_adds_tracks_with_correct_uri_and_metadata(self, mock_speaker):
        from sonos_controller import play_album
        play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        expected_calls = [
            call(build_track_uri(t["track_id"], "3"), build_track_metadata(t))
            for t in SAMPLE_TRACKS
        ]
        mock_speaker.add_uri_to_queue.assert_has_calls(expected_calls)

    def test_starts_playback(self, mock_speaker):
        from sonos_controller import play_album
        play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        mock_speaker.play_from_queue.assert_called_once_with(0)


class TestGetSpeakers:
    def test_returns_speaker_list(self):
        from sonos_controller import get_speakers
        mock_s1 = MagicMock()
        mock_s1.player_name = "Family Room"
        mock_s1.ip_address = "10.0.0.12"
        mock_s2 = MagicMock()
        mock_s2.player_name = "Foyer"
        mock_s2.ip_address = "10.0.0.8"
        with patch("soco.discover", return_value={mock_s1, mock_s2}):
            speakers = get_speakers()
        assert len(speakers) == 2
        names = {s["name"] for s in speakers}
        assert "Family Room" in names
        assert "Foyer" in names

    def test_returns_empty_list_when_none_found(self):
        from sonos_controller import get_speakers
        with patch("soco.discover", return_value=None):
            speakers = get_speakers()
        assert speakers == []
