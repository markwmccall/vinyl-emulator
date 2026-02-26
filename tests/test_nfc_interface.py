import pytest
from unittest.mock import patch


class TestParseTagData:
    def test_valid_apple_tag(self):
        from nfc_interface import parse_tag_data
        assert parse_tag_data("apple:1440903625") == "1440903625"

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
