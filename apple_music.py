import json
import urllib.request
import urllib.parse


def build_track_uri(track_id, sn):
    return f"x-sonos-http:song%3a{track_id}.mp4?sid=204&flags=8232&sn={sn}"


def upgrade_artwork_url(url):
    return url.replace("100x100bb", "600x600bb")



def search_albums(query):
    encoded = urllib.parse.quote(query)
    url = f"https://itunes.apple.com/search?term={encoded}&entity=album"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    return [
        {
            "id": r["collectionId"],
            "name": r["collectionName"],
            "artist": r["artistName"],
            "artwork_url": upgrade_artwork_url(r.get("artworkUrl100", "")),
        }
        for r in data["results"]
    ]


def search_songs(query):
    encoded = urllib.parse.quote(query)
    url = f"https://itunes.apple.com/search?term={encoded}&entity=song"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    return [
        {
            "id": r["trackId"],
            "name": r["trackName"],
            "artist": r["artistName"],
            "album": r["collectionName"],
            "artwork_url": upgrade_artwork_url(r.get("artworkUrl100", "")),
        }
        for r in data["results"]
        if r.get("wrapperType") == "track"
    ]


def get_track(track_id):
    url = f"https://itunes.apple.com/lookup?id={track_id}"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    tracks = [r for r in data["results"] if r.get("wrapperType") == "track"]
    if not tracks:
        return []
    t = tracks[0]
    return [
        {
            "track_id": t["trackId"],
            "name": t["trackName"],
            "track_number": t.get("trackNumber", 1),
            "artist": t["artistName"],
            "album": t["collectionName"],
            "artwork_url": upgrade_artwork_url(t.get("artworkUrl100", "")),
        }
    ]


def get_album_tracks(album_id):
    url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    tracks = [r for r in data["results"] if r.get("wrapperType") == "track"]
    tracks.sort(key=lambda t: t["trackNumber"])
    return [
        {
            "track_id": t["trackId"],
            "name": t["trackName"],
            "track_number": t["trackNumber"],
            "artist": t["artistName"],
            "album": t["collectionName"],
            "artwork_url": upgrade_artwork_url(t.get("artworkUrl100", "")),
        }
        for t in tracks
    ]
