from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class MusicProvider(ABC):
    service_id: str          # tag prefix: "apple"
    display_name: str        # "Apple Music"
    sonos_sid: int           # Sonos URI sid= value (Apple Music = 204)
    sonos_service_type: str  # Sonos UDN service type (Apple Music = "52231")

    @abstractmethod
    def search_albums(self, query: str) -> List[Dict]: ...

    @abstractmethod
    def search_songs(self, query: str) -> List[Dict]: ...

    @abstractmethod
    def get_album_tracks(self, album_id: str) -> List[Dict]: ...

    @abstractmethod
    def get_track(self, track_id: str) -> List[Dict]: ...

    @abstractmethod
    def build_track_uri(self, track_id: str, sn: int) -> str: ...

    @abstractmethod
    def build_track_didl(self, track: Dict, udn: str) -> str: ...

    @abstractmethod
    def lookup_udn(self, speaker, sn: int) -> str: ...

    @abstractmethod
    def detect_sn(self, speaker) -> Optional[str]: ...
