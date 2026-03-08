# Provider Refactor Architecture Plan

## Overview

Pure reorganization — no functionality changes, no new services. Apple Music continues to be
the only working service after the refactor. All 322 tests must remain passing at every step.

The goal is to extract service-specific logic into a `providers/` package with a common
`MusicProvider` ABC, making it straightforward to add Spotify or other services later.

---

## Current State

### What moves where

**`apple_music.py`** (100 lines) — all functions become methods on `AppleMusicProvider`:
- `build_track_uri` → `provider.build_track_uri`
- `search_albums`, `search_songs` → `provider.search_albums`, `provider.search_songs`
- `get_track`, `get_album_tracks` → `provider.get_track`, `provider.get_album_tracks`

**`sonos_controller.py`** — Apple-specific functions move to `AppleMusicProvider`:
- `_APPLE_MUSIC_SERVICE_TYPE = "52231"` → `AppleMusicProvider.sonos_service_type`
- `_lookup_apple_music_udn` → `provider.lookup_udn`
- `_build_track_didl` → `provider.build_track_didl`
- `detect_apple_music_sn` → `provider.detect_sn`
- Generic transport functions stay: `pause`, `resume`, `stop`, `next_track`, `prev_track`,
  `get_volume`, `set_volume`, `get_speakers`, `_rediscover_speaker`

**`nfc_interface.py`** — `parse_tag_data` generalised: remove `apple:` hardcode, add `service`
key to return dict.

---

## Target File Structure

```
providers/
    __init__.py        # registry: get_provider("apple") → AppleMusicProvider instance
    base.py            # MusicProvider ABC
    apple_music.py     # AppleMusicProvider (absorbs apple_music.py + Apple bits of sonos_controller.py)

apple_music.py         # Deleted in Step 9 (becomes a shim in Step 2)
sonos_controller.py    # Generic Sonos/UPnP transport only; takes provider as argument
nfc_interface.py       # parse_tag_data generalised
app.py                 # Uses provider registry; config migration for sn key
```

---

## Provider ABC (`providers/base.py`)

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

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
```

Note: Use `from __future__ import annotations` and `typing` module for Python 3.9 compatibility.
`str | None` and `list[dict]` syntax require Python 3.10+.

---

## Tag Format Change

**Current `parse_tag_data`** — hardcodes `if not tag_string.startswith("apple:"):`
Returns `{"type": "album"|"track", "id": "..."}` — no `service` key.

**New `parse_tag_data`** — parses `{service}:{id}` or `{service}:track:{id}` generically.
Returns `{"service": "apple", "type": "album"|"track", "id": "..."}`.

Backward compatible: `apple:12345` → `{"service": "apple", "type": "album", "id": "12345"}`.

**Behavioural change**: `"spotify:1440903625"` previously raised `ValueError`. Now it returns
`{"service": "spotify", "type": "album", "id": "1440903625"}` and the error moves to the
provider lookup (`get_provider("spotify")` raises `KeyError` if Spotify is not registered).

```python
def parse_tag_data(tag_string):
    if not tag_string or ":" not in tag_string:
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    service, _, rest = tag_string.partition(":")
    if not service or not rest:
        raise ValueError(f"Unrecognised tag format: {tag_string!r}")
    if rest.startswith("track:"):
        track_id = rest[len("track:"):]
        if not track_id:
            raise ValueError(f"Unrecognised tag format: {tag_string!r}")
        return {"service": service, "type": "track", "id": track_id}
    return {"service": service, "type": "album", "id": rest}
```

---

## Config Migration

**Current `config.json`:**
```json
{"speaker_ip": "...", "sn": "3", "nfc_mode": "pn532"}
```

**New `config.json`:**
```json
{"speaker_ip": "...", "nfc_mode": "pn532", "services": {"apple": {"sn": "3"}}}
```

**Migration strategy**: `_load_config()` performs transparent in-memory migration only —
if `sn` exists at top level and `services.apple.sn` does not, migrate the value into
`services.apple.sn` in the returned dict. Do NOT auto-write migration to disk (would break
tests that check saved config).

Also re-expose `config["sn"]` at top level for all existing callsites:

```python
def _load_config():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    # In-memory migration: flat "sn" → services.apple.sn (and vice versa)
    if "sn" in config and "services" not in config:
        config.setdefault("services", {}).setdefault("apple", {})
        config["services"]["apple"]["sn"] = config["sn"]
    elif "services" in config and "apple" in config["services"]:
        config.setdefault("sn", config["services"]["apple"].get("sn"))
    required = ["speaker_ip", "sn", "nfc_mode"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise RuntimeError(f"Missing required config fields: {', '.join(missing)}")
    return config
```

This keeps `config["sn"]` working at all existing callsites in `app.py` with no changes.
The `settings_sonos` POST continues writing `config["sn"]` at top level for now.

---

## `sonos_controller.py` Signature Changes

```python
# Before:
def _do_play_album(speaker, track_dicts, sn): ...
def play_album(speaker_ip, track_dicts, sn, speaker_name=None, config_path=None): ...

# After:
def _do_play_album(speaker, track_dicts, provider, sn): ...
def play_album(speaker_ip, track_dicts, provider, sn, speaker_name=None, config_path=None): ...
```

`get_now_playing` gains optional `providers` parameter (backward-compat default `None`):

```python
def get_now_playing(speaker_ip, providers=None):
    # If providers given, match sid against registered providers.
    # If providers=None, fall back to checking sid=204 (Apple Music default).
```

---

## `app.py` Changes

Replace `import apple_music` and direct calls with provider registry. No service-named
variable lives in `app.py` — `get_provider()` is called at each callsite:

```python
# New imports
from providers import get_provider
```

Key callsite changes:

| Old | New |
|-----|-----|
| `apple_music.search_albums(q)` | `get_provider("apple").search_albums(q)` |
| `apple_music.get_album_tracks(id)` | `get_provider("apple").get_album_tracks(id)` |
| `apple_music.get_track(id)` | `get_provider("apple").get_track(id)` |
| `detect_apple_music_sn(speaker_ip)` | `get_provider("apple").detect_sn(soco.SoCo(speaker_ip))` |
| `play_album(ip, tracks, sn, ...)` | `play_album(ip, tracks, provider, sn, ...)` |
| `tag["id"]` after `parse_tag_data` | also use `tag["service"]` to select provider |

UI routes (search, album detail, etc.) are currently Apple Music-only. The `"apple"` string in
`get_provider("apple")` is intentional — it is honest about the current limitation. When a
`?service=` param is added in a future step, this becomes `get_provider(request.args["service"])`.

NFC-driven paths are already fully generic — the service comes from the tag:
```python
tag = parse_tag_data(tag_data)
provider = get_provider(tag["service"])
tracks = (provider.get_track(tag["id"]) if tag["type"] == "track"
          else provider.get_album_tracks(tag["id"]))
config = _load_config()
play_album(config["speaker_ip"], tracks, provider, config["sn"], ...)
```

---

## Implementation Steps

### Step 1 — Create `providers/` package (new files only, nothing breaks)

Create three new files alongside existing ones. No existing files modified.
All 322 tests pass unchanged.

Files created:
- `providers/__init__.py` — registry with `get_provider(service_id)` and `list_providers()`
- `providers/base.py` — `MusicProvider` ABC
- `providers/apple_music.py` — `AppleMusicProvider` absorbing all Apple-specific logic

### Step 2 — Make `apple_music.py` a backward-compat shim

Replace root `apple_music.py` with re-exports from `providers.apple_music`. The sole purpose
of this shim is to keep `tests/test_apple_music.py` (which does `from apple_music import ...`)
working until Step 6 updates it. It does NOT protect `tests/test_app.py` patches — those are
handled atomically in Step 5.

```python
"""Backward-compatibility shim — only kept for test_apple_music.py.
   Remove once test_apple_music.py is updated (Step 6).
"""
from providers.apple_music import AppleMusicProvider as _p_class, _upgrade_artwork_url

_p = _p_class()
build_track_uri = _p.build_track_uri
upgrade_artwork_url = _upgrade_artwork_url
search_albums = _p.search_albums
search_songs = _p.search_songs
get_track = _p.get_track
get_album_tracks = _p.get_album_tracks
```

Note: `_p` is a separate instance from the registry singleton. This is fine — `test_apple_music.py`
patches at the `urllib.request.urlopen` level, not the provider instance level.

All 322 tests pass unchanged.

### Step 3 — Strip `sonos_controller.py` + update `tests/test_sonos_controller.py` (atomic)

**`sonos_controller.py`:**
- Remove `from apple_music import build_track_uri`
- Remove `_APPLE_MUSIC_SERVICE_TYPE`, `_lookup_apple_music_udn`, `_build_track_didl`
- Add `provider` parameter to `_do_play_album` and `play_album`
- Update `get_now_playing` to accept optional `providers=None`
- **Keep `detect_apple_music_sn` as a one-line shim** — `app.py` still imports it by name
  until Step 5. Replace the body with a delegation to the provider rather than deleting it:
  ```python
  def detect_apple_music_sn(speaker_ip):
      """Deprecated shim — removed in Step 5."""
      from providers.apple_music import AppleMusicProvider
      return AppleMusicProvider().detect_sn(soco.SoCo(speaker_ip))
  ```

**`tests/test_sonos_controller.py`** (simultaneous, atomic with above):
- Remove `from apple_music import build_track_uri` (line 3)
- Replace all `patch("sonos_controller._lookup_apple_music_udn", ...)` with a mock provider:
  ```python
  provider = MagicMock()
  provider.lookup_udn.return_value = SAMPLE_UDN
  provider.build_track_uri.side_effect = lambda track_id, sn: f"x-sonos-http:song%3a{track_id}.mp4?sid=204&flags=8232&sn={sn}"
  provider.build_track_didl.return_value = "<DIDL-Lite>...</DIDL-Lite>"
  play_album("10.0.0.12", SAMPLE_TRACKS, provider, "3")
  ```
- `TestDetectAppleMusicSn`: change import to `providers.apple_music.AppleMusicProvider`;
  call `AppleMusicProvider().detect_sn(mock_speaker)` instead of `detect_apple_music_sn(ip)`
- `TestLookupAppleMusicUdn`: same pattern — `AppleMusicProvider().lookup_udn(speaker, "3")`
- Self-healing tests: add `provider` as 3rd positional arg to `play_album` calls

All 322 tests pass.

### Step 4 — Update `nfc_interface.py` + `tests/test_nfc_interface.py` (atomic)

**Must precede Step 5.** `app.py`'s NFC loop will call `get_provider(tag["service"])`, so
`parse_tag_data` must return `"service"` before those callsites are written.

**`nfc_interface.py`:** Replace `parse_tag_data` with generalised version (see Tag Format
Change section above).

**`tests/test_nfc_interface.py`:**
- `test_valid_album_tag`: add `"service": "apple"` to expected dict
- `test_valid_track_tag`: add `"service": "apple"` to expected dict
- `test_wrong_prefix_raises` → convert to `test_unknown_service_parses_without_error`:
  ```python
  result = parse_tag_data("spotify:1440903625")
  assert result == {"service": "spotify", "type": "album", "id": "1440903625"}
  ```
  The error for unknown services now happens at `get_provider()`, not at parse time.

All 322 tests pass (test converted in-place — net count stays at 322).

### Step 5 — Update `app.py` + `tests/test_app.py` (atomic — the largest single step)

**These two files must be updated together.** The moment a route in `app.py` is rewritten to
call `get_provider(...)` instead of `apple_music.*`, the corresponding test patch target changes.
The shim does NOT protect these patches — patching `app.apple_music.search_albums` only
intercepts calls to the shim's attribute, not calls to `get_provider("apple").search_albums()`.

**`app.py`:**
- Add `from providers import get_provider`
- Remove `import apple_music` (no longer needed once all callsites are migrated)
- Remove `detect_apple_music_sn` from the `from sonos_controller import ...` line (the shim in `sonos_controller.py` is also deleted in this step)
- Update `_load_config()` with migration logic
- Migrate all callsites: `_nfc_loop`, `/play`, `/play/tag`, `/read-tag`, `/detect-sn`,
  `/now-playing`, `/search`, `/album/<id>`, `/track/<id>`, `_format_existing_tag`, `_do_record_tag`
- Update all `play_album(...)` calls to include `provider` as 3rd arg

**`tests/test_app.py`** (simultaneous, atomic with above):

Patch the registry singleton — `providers.get_provider("apple")` always returns the same
instance, so `patch.object` on it intercepts all calls from `app.py`:

```python
# Before:
with patch("app.apple_music.search_albums", return_value=[...]) as mock:

# After:
import providers
with patch.object(providers.get_provider("apple"), "search_albums", return_value=[...]) as mock:
```

Full list of patch targets (~25–30 occurrences):
- `app.apple_music.search_albums` → `patch.object(providers.get_provider("apple"), "search_albums")`
- `app.apple_music.search_songs` → `patch.object(providers.get_provider("apple"), "search_songs")`
- `app.apple_music.get_album_tracks` → `patch.object(providers.get_provider("apple"), "get_album_tracks")`
- `app.apple_music.get_track` → `patch.object(providers.get_provider("apple"), "get_track")`
- `app.detect_apple_music_sn` → `patch.object(providers.get_provider("apple"), "detect_sn")`

`TestDetectSn`: route now calls `get_provider("apple").detect_sn(soco.SoCo(speaker_ip))`.
Test must mock `soco.SoCo` to return a mock speaker and assert `detect_sn` receives it.

`TestLoadConfig.test_missing_sn_raises`: continues to work — `_load_config()` still validates
`sn` (directly in config or migrated from `services.apple.sn`).

`TestSettingsSonos.test_post_saves_speaker_ip_and_sn`: no change — `settings_sonos` POST
continues writing `config["sn"]` at top level.

All 322 tests pass.

### Step 6 — Update `tests/test_apple_music.py` imports

```python
# Before:
from apple_music import search_albums, build_track_uri, ...

# After:
from providers.apple_music import AppleMusicProvider
_p = AppleMusicProvider()
# All test calls via _p.search_albums(...), _p.build_track_uri(...), etc.
```

Patch targets inside these tests use `urllib.request.urlopen` at stdlib level — no change needed.
All 322 tests pass.

### Step 7 — Delete `apple_music.py` shim

Nothing imports root `apple_music` anymore (`app.py` removed it in Step 5,
`test_apple_music.py` updated in Step 6, `sonos_controller.py` in Step 3).

- Delete root `apple_music.py`

Run full test suite. All 322 tests pass.

### Step 8 — Update `config.json.example`

```json
{
  "speaker_ip": "10.0.0.12",
  "speaker_name": "Living Room",
  "nfc_mode": "mock",
  "services": {
    "apple": {
      "sn": "3"
    }
  }
}
```

Documentation only — no test impact.

---

## Test Change Summary

| File | Step | Changes |
|------|------|---------|
| `tests/test_sonos_controller.py` | 3 | Remove `from apple_music import`; replace `_lookup_apple_music_udn` patches with mock provider; add `provider` arg to `play_album` calls; update `detect_sn` / `lookup_udn` import sources |
| `tests/test_nfc_interface.py` | 4 | Add `"service": "apple"` to 2 assertions; convert `test_wrong_prefix_raises` to `test_unknown_service_parses_without_error` |
| `tests/test_app.py` | 5 | Atomic with `app.py` changes; ~25–30 `patch("app.apple_music.*")` → `patch.object(providers.get_provider("apple"), ...)`; update `detect_apple_music_sn` patch; update `TestDetectSn` |
| `tests/test_apple_music.py` | 6 | Update imports to `providers.apple_music.AppleMusicProvider`; wrap calls in instance |
| `tests/conftest.py` | — | No changes — flat config works via `_load_config()` migration |

---

## Potential Pitfalls

### Python 3.9 type syntax
`list[dict]` and `str | None` require Python 3.10+. Use `from __future__ import annotations`
and `typing.List`, `typing.Dict`, `typing.Optional` throughout `providers/`.

### `detect_sn` signature change
Old `detect_apple_music_sn(speaker_ip)` created a SoCo speaker internally.
New `provider.detect_sn(speaker)` takes a SoCo object. The `/detect-sn` route must create
the speaker before calling: `speaker = soco.SoCo(speaker_ip); sn = get_provider("apple").detect_sn(speaker)`.
Tests must mock `soco.SoCo` and assert `detect_sn` receives the returned mock.

### `test_wrong_prefix_raises` behavioural change
`parse_tag_data("spotify:1440903625")` no longer raises. The error for unknown services moves
to the provider lookup layer. This test must be converted (not just updated) — it tests a
behaviour that no longer exists in that function.

### `patch.object` requires the registry singleton
`providers.get_provider("apple")` must return the same instance on every call (registry stores
singletons in a dict). If the registry ever re-instantiates a provider, existing `patch.object`
patches will stop intercepting calls. Ensure `providers/__init__.py` creates each provider once
at import time and returns it from the dict on all subsequent calls.

### Steps 3 and 5 are the riskiest
Step 3 (strip sonos_controller + test_sonos_controller) and Step 5 (app.py + test_app.py
together) touch the most files simultaneously and must be committed atomically.

Step 4 must be completed before Step 5: `app.py`'s NFC loop calls `get_provider(tag["service"])`,
which requires `parse_tag_data` to return a `"service"` key. If the order is reversed, `_nfc_loop`
raises `KeyError: "service"` at runtime.

**The shim (Step 2) does NOT protect `test_app.py` patches.** It only protects
`test_apple_music.py` which imports directly from `apple_music`. Once a route in `app.py` is
rewritten to call `get_provider()`, its test patch must be updated in the same commit.

---

## What Does NOT Change

- All Sonos UPnP transport: `pause`, `resume`, `stop`, `next_track`, `prev_track`, `get_volume`, `set_volume`, `get_speakers`, `_rediscover_speaker`
- Flask route structure and URLs
- Template files (`.html`)
- NFC tag writing (`write_tag`, `write_url_tag`)
- Apple Music functionality: same iTunes API calls, same DIDL format, same URI scheme
- Test count: 322 passing throughout (one test renamed, none removed)
- `smapi_probe.py` — standalone diagnostic script, untouched
