import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_ALBUMS = [
    {"id": 1440903625, "name": "Hysteria", "artist": "Def Leppard",
     "artwork_url": "https://example.com/600x600bb.jpg"},
]

SAMPLE_TRACKS = [
    {"track_id": 1440904001, "name": "Women", "track_number": 1,
     "artist": "Def Leppard", "album": "Hysteria",
     "artwork_url": "https://example.com/600x600bb.jpg"},
    {"track_id": 1440904002, "name": "Rocket", "track_number": 2,
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

    def test_renders_album_and_artist(self, client):
        with patch("app.apple_music.get_album_tracks", return_value=SAMPLE_TRACKS):
            resp = client.get("/album/1440903625")
        assert b"Hysteria" in resp.data
        assert b"Def Leppard" in resp.data


class TestWriteTag:
    def test_calls_write_tag_with_correct_data(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"album_id": "1440903625"})
        assert resp.status_code == 200
        mock_nfc.write_tag.assert_called_once_with("apple:1440903625")

    def test_returns_written_tag_string(self, client, temp_config):
        mock_nfc = MagicMock()
        with patch("app.MockNFC", return_value=mock_nfc):
            resp = client.post("/write-tag", json={"album_id": "1440903625"})
        assert resp.get_json()["written"] == "apple:1440903625"


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
