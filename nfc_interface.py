def parse_tag_data(tag_string):
    """Parse an NDEF tag string into a dict with 'type' and 'id'.

    Supported formats:
      apple:{collection_id}       -> {"type": "album", "id": "..."}
      apple:track:{track_id}      -> {"type": "track", "id": "..."}

    Raises ValueError if the format is not recognised.
    """
    if not tag_string.startswith("apple:"):
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    rest = tag_string[len("apple:"):]
    if not rest:
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    if rest.startswith("track:"):
        track_id = rest[len("track:"):]
        if not track_id:
            raise ValueError(f"Unrecognised tag format: {tag_string!r}")
        return {"type": "track", "id": track_id}
    return {"type": "album", "id": rest}


class MockNFC:
    """Mac/testing NFC implementation — reads from stdin, writes to stdout."""

    def read_tag(self):
        """Block until the user types a tag string and presses Enter."""
        return input("Tap card (or type tag): ")

    def write_tag(self, data):
        """Print what would be written to the physical tag."""
        print(f"[MockNFC] Would write: {data}")
        return True

    def write_url_tag(self, url):
        """Print what URL would be written to the physical tag."""
        print(f"[MockNFC] Would write URL: {url}")
        return True


class PN532NFC:
    """Raspberry Pi NFC implementation using the Waveshare PN532 HAT.

    Not implemented until Phase 5 (hardware deployment).
    """

    def read_tag(self):
        raise NotImplementedError("PN532NFC not yet implemented — Phase 5")

    def write_tag(self, data):
        raise NotImplementedError("PN532NFC not yet implemented — Phase 5")

    def write_url_tag(self, url):
        raise NotImplementedError("PN532NFC not yet implemented — Phase 5")
