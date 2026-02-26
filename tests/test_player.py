import json
import pytest
from unittest.mock import patch, MagicMock, call


SAMPLE_CONFIG = {
    "sn": "3",
    "speaker_ip": "10.0.0.12",
    "nfc_mode": "mock",
}

SAMPLE_TRACKS = [{"track_id": 1440904001, "name": "Women", "track_number": 1,
                  "artist": "Def Leppard", "album": "Hysteria",
                  "artwork_url": "https://example.com/600x600bb.jpg"}]


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(SAMPLE_CONFIG))
    return str(p)


class TestSimulateMode:
    def test_simulate_plays_album(self, config_file):
        from player import run
        with patch("player.get_album_tracks", return_value=SAMPLE_TRACKS) as mock_tracks, \
             patch("player.play_album") as mock_play:
            run(config_path=config_file, simulate="apple:1440903625")
        mock_tracks.assert_called_once_with("1440903625")
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_TRACKS, "3")

    def test_simulate_plays_track(self, config_file):
        from player import run
        with patch("player.get_track", return_value=SAMPLE_TRACKS) as mock_track, \
             patch("player.play_album") as mock_play:
            run(config_path=config_file, simulate="apple:track:1440904001")
        mock_track.assert_called_once_with("1440904001")
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_TRACKS, "3")

    def test_simulate_exits_after_one_play(self, config_file):
        from player import run
        with patch("player.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("player.play_album") as mock_play:
            run(config_path=config_file, simulate="apple:1440903625")
        assert mock_play.call_count == 1

    def test_simulate_invalid_tag_raises(self, config_file):
        from player import run
        with pytest.raises(ValueError):
            run(config_path=config_file, simulate="notvalid")


class TestLoopMode:
    def test_loop_plays_on_tag_read(self, config_file):
        from player import run
        mock_nfc = MagicMock()
        mock_nfc.read_tag.side_effect = ["apple:1440903625", KeyboardInterrupt]
        with patch("player.MockNFC", return_value=mock_nfc), \
             patch("player.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("player.play_album") as mock_play:
            run(config_path=config_file)
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_TRACKS, "3")

    def test_loop_continues_after_bad_tag(self, config_file):
        from player import run
        mock_nfc = MagicMock()
        mock_nfc.read_tag.side_effect = ["notvalid", "apple:1440903625", KeyboardInterrupt]
        with patch("player.MockNFC", return_value=mock_nfc), \
             patch("player.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("player.play_album") as mock_play:
            run(config_path=config_file)
        mock_play.assert_called_once_with("10.0.0.12", SAMPLE_TRACKS, "3")

    def test_loop_continues_after_playback_error(self, config_file):
        from player import run
        mock_nfc = MagicMock()
        mock_nfc.read_tag.side_effect = [
            "apple:1440903625",
            "apple:1440903625",
            KeyboardInterrupt,
        ]
        with patch("player.MockNFC", return_value=mock_nfc), \
             patch("player.get_album_tracks", return_value=SAMPLE_TRACKS), \
             patch("player.play_album", side_effect=[Exception("network error"), None]) as mock_play:
            run(config_path=config_file)
        assert mock_play.call_count == 2


class TestReadMode:
    def test_read_returns_tag_string(self, config_file):
        from player import read_tag_once
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("player.MockNFC", return_value=mock_nfc):
            result = read_tag_once(config_path=config_file)
        assert result == "apple:1440903625"

    def test_read_does_not_play(self, config_file):
        from player import read_tag_once
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("player.MockNFC", return_value=mock_nfc), \
             patch("player.play_album") as mock_play:
            read_tag_once(config_path=config_file)
        mock_play.assert_not_called()

    def test_read_prints_tag(self, config_file, capsys):
        from player import read_tag_once
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("player.MockNFC", return_value=mock_nfc):
            read_tag_once(config_path=config_file)
        captured = capsys.readouterr()
        assert "apple:1440903625" in captured.out

    def test_read_uses_pn532_when_configured(self, tmp_path):
        from player import read_tag_once
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({
            "sn": "3", "speaker_ip": "10.0.0.12", "nfc_mode": "pn532"
        }))
        mock_nfc = MagicMock()
        mock_nfc.read_tag.return_value = "apple:1440903625"
        with patch("player.PN532NFC", return_value=mock_nfc):
            result = read_tag_once(config_path=str(config_file))
        assert result == "apple:1440903625"
