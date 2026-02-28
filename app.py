import argparse
import json
import os
import subprocess
from datetime import datetime

from flask import Flask, abort, jsonify, render_template, request

import apple_music
from nfc_interface import MockNFC, PN532NFC, parse_tag_data
from sonos_controller import detect_apple_music_sn, get_now_playing, get_speakers, pause, play_album, resume, stop

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
TAGS_PATH = os.path.join(os.path.dirname(__file__), "tags.json")


def _load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _load_tags():
    if not os.path.exists(TAGS_PATH):
        return []
    with open(TAGS_PATH) as f:
        return json.load(f)


def _save_tags(tags):
    with open(TAGS_PATH, "w") as f:
        json.dump(tags, f, indent=2)


def _record_tag(tag_string, tag_type, name, artist, artwork_url, album_id=None, track_id=None):
    tags = _load_tags()
    tags = [t for t in tags if t["tag_string"] != tag_string]
    tags.insert(0, {
        "tag_string": tag_string,
        "type": tag_type,
        "name": name,
        "artist": artist,
        "artwork_url": artwork_url,
        "album_id": album_id,
        "track_id": track_id,
        "written_at": datetime.utcnow().isoformat(),
    })
    _save_tags(tags)


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
    if not tracks:
        abort(404)
    return render_template("album.html", album_id=album_id, tracks=tracks)


@app.route("/track/<int:track_id>")
def track(track_id):
    tracks = apple_music.get_track(track_id)
    if not tracks:
        abort(404)
    return render_template("track.html", track_id=track_id, track=tracks[0])


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.route("/write-tag", methods=["POST"])
def write_tag():
    data = request.get_json()
    if not data or ("track_id" not in data and "album_id" not in data):
        return jsonify({"error": "album_id or track_id required"}), 400
    config = _load_config()
    nfc = _make_nfc(config)
    if "track_id" in data:
        tag_data = f"apple:track:{data['track_id']}"
    else:
        tag_data = f"apple:{data['album_id']}"
    nfc.write_tag(tag_data)
    try:
        if "track_id" in data:
            tracks = apple_music.get_track(data["track_id"])
            if tracks:
                t = tracks[0]
                _record_tag(tag_data, "track", t["name"], t["artist"],
                            t.get("artwork_url", ""), album_id=t.get("album_id"),
                            track_id=t["track_id"])
        else:
            tracks = apple_music.get_album_tracks(data["album_id"])
            if tracks:
                t = tracks[0]
                _record_tag(tag_data, "album", t["album"], t["artist"],
                            t.get("artwork_url", ""), album_id=data["album_id"])
    except Exception:
        pass
    return jsonify({"status": "ok", "written": tag_data})


@app.route("/write-url-tag", methods=["POST"])
def write_url_tag():
    url = request.host_url.rstrip("/")
    config = _load_config()
    nfc = _make_nfc(config)
    try:
        nfc.write_url_tag(url)
    except NotImplementedError as e:
        return jsonify({"error": str(e)}), 501
    return jsonify({"status": "ok", "written": url})


@app.route("/play", methods=["POST"])
def play():
    data = request.get_json()
    if not data or ("track_id" not in data and "album_id" not in data):
        return jsonify({"error": "album_id or track_id required"}), 400
    config = _load_config()
    if "track_id" in data:
        tracks = apple_music.get_track(data["track_id"])
    else:
        tracks = apple_music.get_album_tracks(data["album_id"])
    play_album(config["speaker_ip"], tracks, config["sn"],
               speaker_name=config.get("speaker_name"), config_path=CONFIG_PATH)
    return jsonify({"status": "ok"})


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = _load_config()
    saved = False
    if request.method == "POST":
        config["sn"] = request.form.get("sn", config["sn"])
        config["speaker_ip"] = request.form.get("speaker_ip", config["speaker_ip"])
        config["speaker_name"] = request.form.get("speaker_name", config.get("speaker_name", ""))
        config["nfc_mode"] = request.form.get("nfc_mode", config["nfc_mode"])
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        saved = True
    return render_template("settings.html", config=config, saved=saved)


@app.route("/speakers")
def speakers():
    return jsonify(get_speakers())


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


@app.route("/player/status")
def player_status():
    result = subprocess.run(
        ["systemctl", "is-active", "vinyl-player"],
        capture_output=True, text=True
    )
    return jsonify({"status": result.stdout.strip()})


@app.route("/player/control", methods=["POST"])
def player_control():
    data = request.get_json()
    action = data.get("action") if data else None
    if action not in ("stop", "start"):
        return jsonify({"error": "invalid action"}), 400
    subprocess.run(["sudo", "systemctl", action, "vinyl-player"], check=False)
    return jsonify({"status": "ok", "action": action})


@app.route("/detect-sn")
def detect_sn():
    speaker_ip = request.args.get("speaker_ip") or _load_config().get("speaker_ip", "")
    if not speaker_ip:
        return jsonify({"error": "no speaker configured"}), 400
    sn = detect_apple_music_sn(speaker_ip)
    if sn is None:
        return jsonify({"error": "No Apple Music favorites found in Sonos — enter 3 or 5 manually"}), 404
    return jsonify({"sn": sn})



@app.route("/now-playing")
def now_playing():
    config = _load_config()
    if not config.get("speaker_ip"):
        return jsonify({"playing": False})
    info = get_now_playing(config["speaker_ip"])
    if info is None:
        return jsonify({"playing": False})
    result = {
        "playing": True,
        "paused": info["paused"],
        "title": info["title"],
        "artist": info["artist"],
        "album": info["album"],
        "track_id": info["track_id"],
        "album_id": None,
        "artwork_url": None,
    }
    if info["track_id"]:
        tracks = apple_music.get_track(info["track_id"])
        if tracks:
            result["album_id"] = tracks[0].get("album_id")
            result["artwork_url"] = tracks[0].get("artwork_url")
    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/transport", methods=["POST"])
def transport():
    data = request.get_json()
    action = data.get("action") if data else None
    if action not in ("pause", "resume", "stop"):
        return jsonify({"error": "invalid action"}), 400
    config = _load_config()
    name = config.get("speaker_name")
    if action == "pause":
        pause(config["speaker_ip"], speaker_name=name, config_path=CONFIG_PATH)
    elif action == "resume":
        resume(config["speaker_ip"], speaker_name=name, config_path=CONFIG_PATH)
    else:
        stop(config["speaker_ip"], speaker_name=name, config_path=CONFIG_PATH)
    return jsonify({"status": "ok", "action": action})


@app.route("/play/tag", methods=["POST"])
def play_tag():
    data = request.get_json()
    tag_string = data.get("tag") if data else None
    if not tag_string:
        return jsonify({"error": "tag required"}), 400
    try:
        tag = parse_tag_data(tag_string)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    config = _load_config()
    if tag["type"] == "track":
        tracks = apple_music.get_track(tag["id"])
    else:
        tracks = apple_music.get_album_tracks(tag["id"])
    play_album(config["speaker_ip"], tracks, config["sn"],
               speaker_name=config.get("speaker_name"), config_path=CONFIG_PATH)
    return jsonify({"status": "ok"})


@app.route("/collection")
def collection():
    return render_template("collection.html", tags=_load_tags())


@app.route("/collection/delete", methods=["POST"])
def collection_delete():
    data = request.get_json()
    tag_string = data.get("tag_string") if data else None
    if not tag_string:
        return jsonify({"error": "tag_string required"}), 400
    tags = [t for t in _load_tags() if t["tag_string"] != tag_string]
    _save_tags(tags)
    return jsonify({"status": "ok"})


@app.route("/collection/clear", methods=["POST"])
def collection_clear():
    _save_tags([])
    return jsonify({"status": "ok"})


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
