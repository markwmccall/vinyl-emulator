def parse_tag_data(tag_string):
    """Parse an NDEF tag string into an album ID.

    Expected format: apple:{collection_id}
    Returns the collection_id as a string.
    Raises ValueError if the format is not recognised.
    """
    if not tag_string.startswith("apple:"):
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    album_id = tag_string[len("apple:"):]
    if not album_id:
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    return album_id


class MockNFC:
    """Mac/testing NFC implementation — reads from stdin, writes to stdout."""

    def read_tag(self):
        """Block until the user types a tag string and presses Enter."""
        return input("Tap card (or type tag): ")

    def write_tag(self, data):
        """Print what would be written to the physical tag."""
        print(f"[MockNFC] Would write: {data}")
        return True


class PN532NFC:
    """Raspberry Pi NFC implementation using the Waveshare PN532 HAT.

    Not implemented until Phase 5 (hardware deployment).
    """

    def read_tag(self):
        raise NotImplementedError("PN532NFC not yet implemented — Phase 5")

    def write_tag(self, data):
        raise NotImplementedError("PN532NFC not yet implemented — Phase 5")
