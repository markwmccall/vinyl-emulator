import json
import urllib.request
import urllib.parse


def build_track_uri(track_id, sn):
    return f"x-sonos-http:song:{track_id}.mp4?sid=204&flags=8224&sn={sn}"


def upgrade_artwork_url(url):
    return url.replace("100x100bb", "600x600bb")


def build_track_metadata(track):
    return (
        '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"'
        ' xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"'
        ' xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
        '<item id="-1" parentID="-1" restricted="true">'
        f'<dc:title>{track["name"]}</dc:title>'
        '<upnp:class>object.item.audioItem.musicTrack</upnp:class>'
        f'<dc:creator>{track["artist"]}</dc:creator>'
        f'<upnp:album>{track["album"]}</upnp:album>'
        f'<upnp:albumArtURI>{track["artwork_url"]}</upnp:albumArtURI>'
        '</item>'
        '</DIDL-Lite>'
    )


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
            "artwork_url": r.get("artworkUrl100", ""),
        }
        for r in data["results"]
    ]


def get_album_tracks(album_id):
    url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read())
    tracks = [r for r in data["results"] if r["wrapperType"] == "track"]
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
