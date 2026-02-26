import argparse
import json
import os

from flask import Flask, jsonify, render_template, request

import apple_music
import sonos_controller
from nfc_interface import MockNFC, PN532NFC, parse_tag_data
from sonos_controller import play_album

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def _load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _make_nfc(config):
    if config.get("nfc_mode") == "pn532":
        return PN532NFC()
    return MockNFC()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    search_type = request.args.get("type", "album")
    if not q:
        return jsonify([])
    if search_type == "song":
        return jsonify(apple_music.search_songs(q))
    return jsonify(apple_music.search_albums(q))


@app.route("/album/<int:album_id>")
def album(album_id):
    tracks = apple_music.get_album_tracks(album_id)
    return render_template("album.html", album_id=album_id, tracks=tracks)


@app.route("/track/<int:track_id>")
def track(track_id):
    tracks = apple_music.get_track(track_id)
    t = tracks[0] if tracks else None
    return render_template("track.html", track_id=track_id, track=t)


@app.route("/write-tag", methods=["POST"])
def write_tag():
    data = request.get_json()
    config = _load_config()
    nfc = _make_nfc(config)
    if "track_id" in data:
        tag_data = f"apple:track:{data['track_id']}"
    else:
        tag_data = f"apple:{data['album_id']}"
    nfc.write_tag(tag_data)
    return jsonify({"status": "ok", "written": tag_data})


@app.route("/play", methods=["POST"])
def play():
    data = request.get_json()
    config = _load_config()
    if "track_id" in data:
        tracks = apple_music.get_track(data["track_id"])
    else:
        tracks = apple_music.get_album_tracks(data["album_id"])
    play_album(config["speaker_ip"], tracks, config["sn"])
    return jsonify({"status": "ok"})


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = _load_config()
    saved = False
    if request.method == "POST":
        config["sn"] = request.form.get("sn", config["sn"])
        config["speaker_ip"] = request.form.get("speaker_ip", config["speaker_ip"])
        config["nfc_mode"] = request.form.get("nfc_mode", config["nfc_mode"])
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        saved = True
    return render_template("settings.html", config=config, saved=saved)


@app.route("/speakers")
def speakers():
    return jsonify(sonos_controller.get_speakers())


@app.route("/read-tag")
def read_tag():
    config = _load_config()
    tag_string = request.args.get("tag")
    if tag_string is None:
        nfc = _make_nfc(config)
        tag_string = nfc.read_tag()
    try:
        tag = parse_tag_data(tag_string)
    except ValueError as e:
        return jsonify({"tag_string": tag_string, "tag_type": None, "content_id": None,
                        "album": None, "error": str(e)})
    tag_type = tag["type"]
    content_id = tag["id"]
    if tag_type == "track":
        tracks = apple_music.get_track(content_id)
    else:
        tracks = apple_music.get_album_tracks(content_id)
    album = None
    if tracks:
        t = tracks[0]
        album = {"name": t["album"], "artist": t["artist"], "artwork_url": t["artwork_url"]}
    return jsonify({"tag_string": tag_string, "tag_type": tag_type, "content_id": content_id,
                    "album": album, "error": None})


@app.route("/verify")
def verify():
    config = _load_config()
    return render_template("verify.html", nfc_mode=config.get("nfc_mode", "mock"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vinyl emulator web UI")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind to (use 0.0.0.0 for Pi)")
    args = parser.parse_args()
    app.run(host=args.host, port=5000)
