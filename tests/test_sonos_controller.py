from unittest.mock import patch, MagicMock
from apple_music import build_track_uri

SAMPLE_UDN = "SA_RINCON52231_X_#Svc52231-f7c0f087-Token"

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


def _get_enqueued(mock_speaker, call_index):
    """Extract the EnqueuedURI and EnqueuedURIMetaData from an AddURIToQueue call."""
    call_params = dict(mock_speaker.avTransport.AddURIToQueue.call_args_list[call_index][0][0])
    return call_params["EnqueuedURI"], call_params["EnqueuedURIMetaData"]


class TestPlayAlbum:
    def test_clears_queue_first(self, mock_speaker):
        from sonos_controller import play_album
        with patch("sonos_controller._lookup_apple_music_udn", return_value=SAMPLE_UDN):
            play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        mock_speaker.clear_queue.assert_called_once()

    def test_adds_all_tracks(self, mock_speaker):
        from sonos_controller import play_album
        with patch("sonos_controller._lookup_apple_music_udn", return_value=SAMPLE_UDN):
            play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        assert mock_speaker.avTransport.AddURIToQueue.call_count == 2

    def test_adds_tracks_with_correct_metadata(self, mock_speaker):
        from sonos_controller import play_album
        with patch("sonos_controller._lookup_apple_music_udn", return_value=SAMPLE_UDN):
            play_album("10.0.0.12", SAMPLE_TRACKS, "3")

        uri0, meta0 = _get_enqueued(mock_speaker, 0)
        assert uri0 == build_track_uri(SAMPLE_TRACKS[0]["track_id"], "3")
        assert "<dc:title>Women</dc:title>" in meta0
        assert f"10032028song%3a{SAMPLE_TRACKS[0]['track_id']}" in meta0
        assert SAMPLE_UDN in meta0

        uri1, meta1 = _get_enqueued(mock_speaker, 1)
        assert uri1 == build_track_uri(SAMPLE_TRACKS[1]["track_id"], "3")
        assert "<dc:title>Rocket</dc:title>" in meta1
        assert f"10032028song%3a{SAMPLE_TRACKS[1]['track_id']}" in meta1

    def test_metadata_uses_apple_music_desc(self, mock_speaker):
        from sonos_controller import play_album
        with patch("sonos_controller._lookup_apple_music_udn", return_value=SAMPLE_UDN):
            play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        _, meta = _get_enqueued(mock_speaker, 0)
        assert "SA_RINCON52231_" in meta
        assert "RINCON_AssociatedZPUDN" not in meta

    def test_starts_playback(self, mock_speaker):
        from sonos_controller import play_album
        with patch("sonos_controller._lookup_apple_music_udn", return_value=SAMPLE_UDN):
            play_album("10.0.0.12", SAMPLE_TRACKS, "3")
        mock_speaker.play_from_queue.assert_called_once_with(0)

    def test_does_nothing_for_empty_track_list(self, mock_speaker):
        from sonos_controller import play_album
        play_album("10.0.0.12", [], "3")
        mock_speaker.clear_queue.assert_not_called()
        mock_speaker.play_from_queue.assert_not_called()


class TestDetectAppleMusicSn:
    def test_returns_sn_from_favorites(self, mock_speaker):
        xml = (
            '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
            '<item><res protocolInfo="sonos.com-http:*:audio/mp4:*">'
            'x-sonos-http:song%3A1440904001.mp4?sid=204&amp;flags=8232&amp;sn=3'
            '</res></item>'
            '</DIDL-Lite>'
        )
        mock_speaker.contentDirectory.Browse.return_value = {"Result": xml}
        from sonos_controller import detect_apple_music_sn
        assert detect_apple_music_sn("10.0.0.12") == "3"

    def test_ignores_non_apple_music_services(self, mock_speaker):
        xml = (
            '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
            '<item><res protocolInfo="x-sonosapi-stream:*:*:*">'
            'x-sonosapi-stream:s23895?sid=333&amp;flags=8292&amp;sn=7'
            '</res></item>'
            '</DIDL-Lite>'
        )
        mock_speaker.contentDirectory.Browse.return_value = {"Result": xml}
        from sonos_controller import detect_apple_music_sn
        assert detect_apple_music_sn("10.0.0.12") is None

    def test_returns_none_when_no_apple_music_favorites(self, mock_speaker):
        mock_speaker.contentDirectory.Browse.return_value = {"Result": "<DIDL-Lite></DIDL-Lite>"}
        from sonos_controller import detect_apple_music_sn
        assert detect_apple_music_sn("10.0.0.12") is None

    def test_returns_none_on_exception(self, mock_speaker):
        mock_speaker.contentDirectory.Browse.side_effect = Exception("network error")
        from sonos_controller import detect_apple_music_sn
        assert detect_apple_music_sn("10.0.0.12") is None


class TestTransport:
    def test_pause_calls_speaker_pause(self, mock_speaker):
        from sonos_controller import pause
        pause("10.0.0.12")
        mock_speaker.pause.assert_called_once()

    def test_resume_calls_speaker_play(self, mock_speaker):
        from sonos_controller import resume
        resume("10.0.0.12")
        mock_speaker.play.assert_called_once()

    def test_stop_calls_speaker_stop(self, mock_speaker):
        from sonos_controller import stop
        stop("10.0.0.12")
        mock_speaker.stop.assert_called_once()


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
