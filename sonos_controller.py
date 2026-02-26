import soco
from apple_music import build_track_uri, build_track_metadata


def get_speakers():
    devices = soco.discover() or []
    return [{"name": d.player_name, "ip": d.ip_address} for d in devices]


def play_album(speaker_ip, track_dicts, sn):
    speaker = soco.SoCo(speaker_ip)
    speaker.clear_queue()
    for track in track_dicts:
        uri = build_track_uri(track["track_id"], sn)
        metadata = build_track_metadata(track)
        speaker.add_uri_to_queue(uri, metadata)
    speaker.play_from_queue(0)
