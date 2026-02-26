import argparse
import json
import logging

from apple_music import get_album_tracks
from nfc_interface import MockNFC, PN532NFC, parse_tag_data
from sonos_controller import play_album

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.json"


def _load_config(config_path):
    with open(config_path) as f:
        return json.load(f)


def _make_nfc(nfc_mode):
    if nfc_mode == "pn532":
        return PN532NFC()
    return MockNFC()


def run(config_path=DEFAULT_CONFIG_PATH, simulate=None):
    config = _load_config(config_path)
    speaker_ip = config["speaker_ip"]
    sn = config["sn"]
    nfc_mode = config.get("nfc_mode", "mock")

    if simulate is not None:
        album_id = parse_tag_data(simulate)
        tracks = get_album_tracks(album_id)
        play_album(speaker_ip, tracks, sn)
        return

    nfc = _make_nfc(nfc_mode)
    log.info("Vinyl emulator running. Tap a card to play.")
    while True:
        try:
            tag_data = nfc.read_tag()
            album_id = parse_tag_data(tag_data)
            tracks = get_album_tracks(album_id)
            play_album(speaker_ip, tracks, sn)
            log.info(f"Playing album {album_id}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vinyl emulator player")
    parser.add_argument(
        "--simulate",
        metavar="TAG",
        help="Play once using this tag string (e.g. apple:1440903625) and exit",
    )
    args = parser.parse_args()
    run(simulate=args.simulate)
