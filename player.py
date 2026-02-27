import argparse
import json
import logging
import os

from apple_music import get_album_tracks, get_track
from nfc_interface import MockNFC, PN532NFC, parse_tag_data
from sonos_controller import play_album

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _load_config(config_path):
    with open(config_path) as f:
        return json.load(f)


def _make_nfc(nfc_mode):
    if nfc_mode == "pn532":
        return PN532NFC()
    return MockNFC()


def read_tag_once(config_path=DEFAULT_CONFIG_PATH):
    config = _load_config(config_path)
    nfc_mode = config.get("nfc_mode", "mock")
    nfc = _make_nfc(nfc_mode)
    tag_data = nfc.read_tag()
    print(tag_data)
    return tag_data


def run(config_path=DEFAULT_CONFIG_PATH, simulate=None):
    config = _load_config(config_path)
    speaker_ip = config["speaker_ip"]
    sn = config["sn"]
    nfc_mode = config.get("nfc_mode", "mock")

    if simulate is not None:
        tag = parse_tag_data(simulate)
        tracks = get_track(tag["id"]) if tag["type"] == "track" else get_album_tracks(tag["id"])
        play_album(speaker_ip, tracks, sn)
        return

    nfc = _make_nfc(nfc_mode)
    log.info("Vinyl emulator running. Tap a card to play.")
    while True:
        try:
            tag_data = nfc.read_tag()
            tag = parse_tag_data(tag_data)
            tracks = get_track(tag["id"]) if tag["type"] == "track" else get_album_tracks(tag["id"])
            play_album(speaker_ip, tracks, sn)
            log.info(f"Playing {tag['type']} {tag['id']}")
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
    parser.add_argument(
        "--read",
        action="store_true",
        help="Read one NFC tag, print its content, and exit (no music played)",
    )
    args = parser.parse_args()
    if args.read:
        read_tag_once()
    else:
        run(simulate=args.simulate)
