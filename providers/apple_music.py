import html
import json
import re
import urllib.parse
import urllib.request
import xml.sax.saxutils as saxutils
from typing import Dict, List, Optional

from providers.base import MusicProvider


def _upgrade_artwork_url(url):
    return url.replace("100x100bb", "600x600bb")


def _format_duration(ms):
    if not ms:
        return ""
    s = int(ms) // 1000
    return f"{s // 60}:{s % 60:02d}"


class AppleMusicProvider(MusicProvider):
    service_id = "apple"
    display_name = "Apple Music"
    sonos_sid = 204
    sonos_service_type = "52231"

    def search_albums(self, query: str) -> List[Dict]:
        encoded = urllib.parse.quote(query)
        url = f"https://itunes.apple.com/search?term={encoded}&entity=album"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
        return [
            {
                "id": r["collectionId"],
                "name": r["collectionName"],
                "artist": r["artistName"],
                "artwork_url": _upgrade_artwork_url(r.get("artworkUrl100", "")),
            }
            for r in data["results"]
        ]

    def search_songs(self, query: str) -> List[Dict]:
        encoded = urllib.parse.quote(query)
        url = f"https://itunes.apple.com/search?term={encoded}&entity=song"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
        return [
            {
                "id": r["trackId"],
                "name": r["trackName"],
                "artist": r["artistName"],
                "album": r["collectionName"],
                "artwork_url": _upgrade_artwork_url(r.get("artworkUrl100", "")),
            }
            for r in data["results"]
            if r.get("wrapperType") == "track"
        ]

    def get_album_tracks(self, album_id: str) -> List[Dict]:
        url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())
        collection = next(
            (r for r in data["results"] if r.get("wrapperType") == "collection"), None
        )
        release_year = collection.get("releaseDate", "")[:4] if collection else ""
        copyright_line = collection.get("copyright", "") if collection else ""
        tracks = [r for r in data["results"] if r.get("wrapperType") == "track"]
        tracks.sort(key=lambda t: (t.get("discNumber", 1), t["trackNumber"]))
        return [
            {
                "track_id": t["trackId"],
                "name": t["trackName"],
                "track_number": t["trackNumber"],
                "artist": t["artistName"],
                "album": t["collectionName"],
                "album_id": t.get("collectionId"),
                "artwork_url": _upgrade_artwork_url(t.get("artworkUrl100", "")),
                "duration": _format_duration(t.get("trackTimeMillis")),
                "release_year": release_year,
                "copyright": copyright_line,
            }
            for t in tracks
        ]

    def get_track(self, track_id: str) -> List[Dict]:
        url = f"https://itunes.apple.com/lookup?id={track_id}"
        with urllib.request.urlopen(url, timeout=10) as response:
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
                "album_id": t.get("collectionId"),
                "artwork_url": _upgrade_artwork_url(t.get("artworkUrl100", "")),
            }
        ]

    def build_track_uri(self, track_id: str, sn: int) -> str:
        return f"x-sonos-http:song%3a{track_id}.mp4?sid=204&flags=8232&sn={sn}"

    def build_track_didl(self, track: Dict, udn: str) -> str:
        """Build DIDL-Lite metadata matching the native Sonos app format.

        Uses the Sonos content-browser item ID format (10032028song%3a{track_id})
        so Sonos can resolve the SMAPI GetMediaMetadata call and populate the
        queue with full title/artist/album metadata from Apple Music.
        """
        e = saxutils.escape
        item_id = f"10032028song%3a{track['track_id']}"
        return (
            '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"'
            ' xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"'
            ' xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"'
            ' xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">'
            f'<item id="{item_id}" parentID="{item_id}" restricted="true">'
            f'<dc:title>{e(track["name"])}</dc:title>'
            '<upnp:class>object.item.audioItem.musicTrack</upnp:class>'
            f'<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">{e(udn)}</desc>'
            '</item>'
            '</DIDL-Lite>'
        )

    def lookup_udn(self, speaker, sn: int) -> str:
        """Find the Apple Music account UDN for the given serial number by scanning
        Sonos favorites, which store the full authenticated account UDN in their
        DIDL metadata. Falls back to the bare service-type UDN if not found.
        """
        fallback = f"SA_RINCON{self.sonos_service_type}_"
        try:
            result = speaker.contentDirectory.Browse([
                ("ObjectID", "FV:2"),
                ("BrowseFlag", "BrowseDirectChildren"),
                ("Filter", "*"),
                ("StartingIndex", 0),
                ("RequestedCount", 100),
                ("SortCriteria", ""),
            ])
            data = result.get("Result", "")
            for res_uri, resmd_raw in re.findall(
                r"<[^>]+:res[^>]*>([^<]*)</[^>]+:res>.*?<[^>]+:resMD>([^<]*)</[^>]+:resMD>",
                data,
                re.DOTALL,
            ):
                if f"sn={sn}" not in res_uri:
                    continue
                decoded = html.unescape(resmd_raw)
                m = re.search(
                    r"SA_RINCON" + self.sonos_service_type + r"[^<\"&\s]{0,80}", decoded
                )
                if m:
                    return m.group(0)
        except Exception:
            pass
        return fallback

    def detect_sn(self, speaker) -> Optional[str]:
        """Scan Sonos favorites for an Apple Music URI and extract the sn value.

        Returns the sn as a string, or None if not found (e.g., no Apple Music
        favorites saved in Sonos).
        """
        try:
            result = speaker.contentDirectory.Browse([
                ("ObjectID", "FV:2"),
                ("BrowseFlag", "BrowseDirectChildren"),
                ("Filter", "*"),
                ("StartingIndex", 0),
                ("RequestedCount", 100),
                ("SortCriteria", ""),
            ])
            data = result.get("Result", "")
            for res_uri in re.findall(
                r"<(?:[^>]+:)?res[^>]*>([^<]*)</(?:[^>]+:)?res>", data
            ):
                uri = html.unescape(res_uri)
                if f"sid={self.sonos_sid}" not in uri:
                    continue
                m = re.search(r"[?&]sn=(\d+)", uri)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None
