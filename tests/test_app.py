import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_ALBUMS = [
    {"id": 1440903625, "name": "Hysteria", "artist": "Def Leppard",
     "artwork_url": "https://example.com/600x600bb.jpg"},
]

SAMPLE_SONGS = [
    {"id": 1440904001, "name": "Women", "artist": "Def Leppard",
     "album": "Hysteria", "artwork_url": "https://example.com/600x600bb.jpg"},
]

SAMPLE_TRACKS = [
    {"track_id": 1440904001, "name": "Women", "track_number": 1,
     "artist": "Def Leppard", "album": "Hysteria",
     "artwork_url": "https://example.com/600x600bb.jpg"},
    {"track_id": 1440904002, "name": "Rocket", "track_number": 2,
     "artist": "Def Leppard", "album": "Hysteria",
     "artwork_url": "https://example.com/600x600bb.jpg"},
]

SAMPLE_SINGLE_TRACK = [
    {"track_id": 1440904001, "name": "Women", "track_number": 1,
     "artist": "Def Leppard", "album": "Hysteria",
     "artwork_url": "https://example.com/600x600bb.jpg"},
]


class TestIndex:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_renders_search_form(self, client):
        resp = client.get("/")
        assert b"search" in resp.data.lower()


class TestSearch:
    def test_returns_json_albums(self, client):
        with patch("app.apple_music.search_albums", return_value=SAMPLE_ALBUMS):
            resp = client.get("/search?q=Hysteria")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Hysteria"
        assert data[0]["artist"] == "Def Leppard"

    def test_song_search_returns_songs(self, client):
        with patch("app.apple_music.search_songs", return_value=SAMPLE_SONGS):
            resp = client.get("/search?q=Women&type=song")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["name"] == "Women"
        assert data[0]["album"] == "Hysteria"

    def test_empty_query_returns_empty_list(self, client):
        resp = client.get("/search?q=")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_missing_query_returns_empty_list(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestAlbum:
    def test_returns_200(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert resp.status_code == 200

    def test_renders_track_names(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"Women" in resp.data
        assert b"Rocket" in resp.data

    def test_track_names_are_linked(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"/track/1440904001" in resp.data
        assert b"/track/1440904002" in resp.data

    def test_renders_album_and_artist(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"Hysteria" in resp.data
        assert b"Def Leppard" in resp.data


class TestTrack:
    def test_returns_200(self, client):
        with patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK):
            resp = client.get("/track/1440904001")
        assert resp.status_code == 200

    def test_renders_track_name(self, client):
        with patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK):
            resp = client.get("/track/1440904001")
        assert b"Women" in resp.data

    def test_renders_artist_and_album(self, client):
        with patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK):
            resp = client.get("/track/1440904001")
        assert b"Def Leppard" in resp.data
        assert b"Hysteria" in resp.data

    def test_shows_tag_string(self, client):
        with patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK):
            resp = client.get("/track/1440904001")
        assert b"apple:track:1440904001" in resp.data


class TestWriteTag:
    def test_calls_write_tag_with_album_data(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"album_id": "1440903625"})
        assert resp.status_code == 200
        mock_nfc.write_tag.assert_called_once_with("apple:1440903625")

    def test_returns_written_album_tag_string(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"album_id": "1440903625"})
        assert resp.get_json()["written"] == "apple:1440903625"

    def test_calls_write_tag_with_track_data(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"track_id": "1440904001"})
        assert resp.status_code == 200
        mock_nfc.write_tag.assert_called_once_with("apple:track:1440904001")

    def test_returns_written_track_tag_string(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"track_id": "1440904001"})
        assert resp.get_json()["written"] == "apple:track:1440904001"


class TestAlbumPage:
    def test_shows_album_id(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"1440903625" in resp.data

    def test_shows_tag_string(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"apple:1440903625" in resp.data


class TestPlay:
    def test_plays_album(self, client, temp_config):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("app.play_album") as mock_play:
            resp = client.post("/play", json={"album_id": "1440903625"})
        assert resp.status_code == 200
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_TRACKS, "3")

    def test_plays_track(self, client, temp_config):
        with patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK), \
             patch("app.play_album") as mock_play:
            resp = client.post("/play", json={"track_id": "1440904001"})
        assert resp.status_code == 200
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_SINGLE_TRACK, "3")

    def test_returns_ok(self, client, temp_config):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("app.play_album"):
            resp = client.post("/play", json={"album_id": "1440903625"})
        assert resp.get_json()["status"] == "ok"


class TestSettings:
    def test_get_returns_200(self, client, temp_config):
        resp = client.get("/settings")
        assert resp.status_code == 200

    def test_get_renders_current_config(self, client, temp_config):
        resp = client.get("/settings")
        assert b"10.0.0.12" in resp.data

    def test_post_saves_config(self, client, temp_config):
        client.post("/settings", data={
            "sn": "5",
            "speaker_ip": "10.0.0.8",
            "nfc_mode": "mock",
        })
        saved = json.loads(temp_config.read_text())
        assert saved["sn"] == "5"
        assert saved["speaker_ip"] == "10.0.0.8"

    def test_post_returns_200(self, client, temp_config):
        resp = client.post("/settings", data={
            "sn": "3",
            "speaker_ip": "10.0.0.12",
            "nfc_mode": "mock",
        })
        assert resp.status_code == 200


class TestSpeakers:
    def test_returns_json_list(self, client):
        with patch("app.sonos_controller.get_speakers", return_value=[
            {"name": "Family Room", "ip": "10.0.0.12"},
            {"name": "Foyer", "ip": "10.0.0.8"},
        ]):
            resp = client.get("/speakers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["name"] == "Family Room"


class TestReadTag:
    def test_album_tag_returns_content_id_and_type(self, client, temp_config):
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("app.MockNFC", return_value=mock_nfc), \
             patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/read-tag")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tag_string"] == "apple:1440903625"
        assert data["tag_type"] == "album"
        assert data["content_id"] == "1440903625"

    def test_track_tag_returns_content_id_and_type(self, client, temp_config):
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:track:1440904001"
        with patch("app.MockNFC", return_value=mock_nfc), \
             patch("app.apple_music.get_track", return_value=SAMPLE_SINGLE_TRACK):
            resp = client.get("/read-tag")
        data = resp.get_json()
        assert data["tag_string"] == "apple:track:1440904001"
        assert data["tag_type"] == "track"
        assert data["content_id"] == "1440904001"

    def test_returns_album_info(self, client, temp_config):
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("app.MockNFC", return_value=mock_nfc), \
             patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/read-tag")
        data = resp.get_json()
        assert data["album"]["name"] == "Hysteria"
        assert data["album"]["artist"] == "Def Leppard"
        assert "artwork_url" in data["album"]

    def test_invalid_tag_returns_error(self, client, temp_config):
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "notvalid"
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.get("/read-tag")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["error"] is not None

    def test_tag_query_param_skips_nfc(self, client, temp_config):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/read-tag?tag=apple:1440903625")
        data = resp.get_json()
        assert data["tag_string"] == "apple:1440903625"
        assert data["content_id"] == "1440903625"


class TestVerify:
    def test_returns_200(self, client):
        resp = client.get("/verify")
        assert resp.status_code == 200

    def test_renders_read_tag_button(self, client):
        resp = client.get("/verify")
        assert b"read" in resp.data.lower() or b"tap" in resp.data.lower()
