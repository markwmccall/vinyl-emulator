import json
import pytest
from unittest.mock import MagicMock


# --- iTunes API sample data ---

SAMPLE_SEARCH_RESPONSE = {
    "resultCount": 1,
    "results": [
        {
            "wrapperType": "collection",
            "collectionId": 1440903625,
            "collectionName": "Hysteria",
            "artistName": "Def Leppard",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        }
    ],
}

# Note: first item is the album row (wrapperType "collection") — must be filtered out
SAMPLE_SONG_SEARCH_RESPONSE = {
    "resultCount": 2,
    "results": [
        {
            "wrapperType": "track",
            "trackId": 1440904001,
            "trackName": "Women",
            "trackNumber": 1,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
        {
            "wrapperType": "track",
            "trackId": 1440904002,
            "trackName": "Rocket",
            "trackNumber": 2,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
    ],
}

SAMPLE_TRACK_LOOKUP_RESPONSE = {
    "resultCount": 1,
    "results": [
        {
            "wrapperType": "track",
            "trackId": 1440904001,
            "trackName": "Women",
            "trackNumber": 1,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
    ],
}

SAMPLE_LOOKUP_RESPONSE = {
    "resultCount": 3,
    "results": [
        {
            "wrapperType": "collection",
            "collectionId": 1440903625,
            "collectionName": "Hysteria",
            "artistName": "Def Leppard",
        },
        {
            "wrapperType": "track",
            "trackId": 1440904001,
            "trackName": "Women",
            "trackNumber": 1,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
        {
            "wrapperType": "track",
            "trackId": 1440904002,
            "trackName": "Rocket",
            "trackNumber": 2,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
    ],
}


# --- Mock SoCo speaker ---

@pytest.fixture
def mock_speaker(mocker):
    speaker = MagicMock()
    mocker.patch("soco.SoCo", return_value=speaker)
    return speaker


# --- Flask test client ---

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Temp config file ---

@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "sn": "3",
        "speaker_ip": "10.0.0.12",
        "speaker_name": "Family Room",
        "nfc_mode": "mock"
    }))
    import app
    monkeypatch.setattr(app, "CONFIG_PATH", str(config_file))
    return config_file
