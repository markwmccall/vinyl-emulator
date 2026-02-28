import pytest
from unittest.mock import patch


class TestParseTagData:
    def test_valid_album_tag(self):
        from nfc_interface import parse_tag_data
        assert parse_tag_data("apple:1440903625") == {"type": "album", "id": "1440903625"}

    def test_valid_track_tag(self):
        from nfc_interface import parse_tag_data
        assert parse_tag_data("apple:track:1440904001") == {"type": "track", "id": "1440904001"}

    def test_invalid_format_raises(self):
        from nfc_interface import parse_tag_data
        with pytest.raises(ValueError):
            parse_tag_data("notvalid")

    def test_wrong_prefix_raises(self):
        from nfc_interface import parse_tag_data
        with pytest.raises(ValueError):
            parse_tag_data("spotify:1440903625")

    def test_empty_string_raises(self):
        from nfc_interface import parse_tag_data
        with pytest.raises(ValueError):
            parse_tag_data("")

    def test_apple_with_no_id_raises(self):
        from nfc_interface import parse_tag_data
        with pytest.raises(ValueError):
            parse_tag_data("apple:")

    def test_track_with_no_id_raises(self):
        from nfc_interface import parse_tag_data
        with pytest.raises(ValueError):
            parse_tag_data("apple:track:")


class TestMockNFC:
    def test_read_tag_returns_input(self):
        from nfc_interface import MockNFC
        nfc = MockNFC()
        with patch("builtins.input", return_value="apple:1440903625"):
            result = nfc.read_tag()
        assert result == "apple:1440903625"

    def test_write_tag_returns_true(self):
        from nfc_interface import MockNFC
        nfc = MockNFC()
        assert nfc.write_tag("apple:1440903625") is True

    def test_write_url_tag_returns_true(self):
        from nfc_interface import MockNFC
        nfc = MockNFC()
        assert nfc.write_url_tag("http://10.0.0.71:5000") is True


class TestPN532NFC:
    def test_read_tag_not_implemented(self):
        from nfc_interface import PN532NFC
        nfc = PN532NFC()
        with pytest.raises(NotImplementedError):
            nfc.read_tag()

    def test_write_tag_not_implemented(self):
        from nfc_interface import PN532NFC
        nfc = PN532NFC()
        with pytest.raises(NotImplementedError):
            nfc.write_tag("apple:1440903625")

    def test_write_url_tag_not_implemented(self):
        from nfc_interface import PN532NFC
        nfc = PN532NFC()
        with pytest.raises(NotImplementedError):
            nfc.write_url_tag("http://10.0.0.71:5000")
