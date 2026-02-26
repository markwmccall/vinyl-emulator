# Apple Music Vinyl Emulator — Implementation Plan

## Context
Build a physical vinyl emulator: placing an NFC card on a reader triggers that album to play on Sonos via Apple Music. Hardware is a Raspberry Pi Zero W + Waveshare PN532 NFC HAT + NTAG213 tags. All coding and testing happens on Mac first using emulated NFC — hardware is only introduced at the end.

## Development Approach: Test Driven Development (TDD)
Write a failing test first, implement the minimum code to make it pass, repeat. This applies to all core modules. The web UI uses Flask's test client for route testing. The player loop is thin orchestration and is covered by integration testing via the terminal.

Test infrastructure:
- Framework: `pytest`
- HTTP mocking: `unittest.mock.patch` on `urllib.request.urlopen`
- SoCo mocking: `unittest.mock.patch` on `soco.SoCo`
- Shared fixtures: `tests/conftest.py`
- File system tests: monkeypatch `app.CONFIG_PATH` to a temp file (see app.py design)

---

## Confirmed Technical Facts (from prototype testing)
- `sn=3` — account-specific Sonos/Apple Music service number, confirmed stable
- Album URI format (`x-rincon-cpcontainer`) fails with UPnP Error 714 — confirmed dead end, not a config issue
- Working URI: `x-sonos-http:song:{track_id}.mp4?sid=204&flags=8224&sn=3`
- Album playback requires queuing individual tracks — confirmed by inspecting Sonos queue during native app playback
- iTunes Search API provides usable track IDs (no auth required)
- Full album tracklist: `https://itunes.apple.com/lookup?id={album_id}&entity=song`
  - Returns album row first (`wrapperType: "collection"`) then tracks (`wrapperType: "track"`)
  - Must filter to `wrapperType == "track"` before sorting by `trackNumber`
- Album search: `https://itunes.apple.com/search?term={query}&entity=album`
- iTunes API key field names: `trackId`, `collectionId`, `artistName`, `trackName`, `collectionName`, `artworkUrl100`, `trackNumber`, `wrapperType`
- Artwork URL: `artworkUrl100` is 100×100px — replace `100x100bb` with `600x600bb` in URL for higher resolution; `get_album_tracks` applies this internally so all returned dicts already have high-res URLs
- Behavior on new tag scan: replace immediately (stop current, start new)
- Speaker: global default set in config (single speaker, no per-tag)
- Mac environment: Python 3.9, use `python3` / `pip3`

---

## Project Structure
```
vinyl-emulator/
├── config.json           # sn value, default speaker IP, nfc_mode — NOT committed to git
├── config.example.json   # Safe template, committed to git
├── .gitignore            # Excludes config.json, __pycache__, *.pyc
├── README.md
├── apple_music.py        # iTunes API functions
├── sonos_controller.py   # SoCo queue management
├── nfc_interface.py      # Abstract NFC layer (mock or real) + parse_tag_data
├── player.py             # Main loop — uses nfc_interface, works on Mac and Pi
├── app.py                # Flask web UI
├── templates/
│   ├── base.html         # Shared layout
│   ├── index.html        # Album search
│   ├── album.html        # Album detail + write tag
│   └── settings.html     # Speaker IP + sn config
├── static/
│   └── style.css
├── tests/
│   ├── conftest.py       # Shared fixtures and mocks
│   ├── test_apple_music.py
│   ├── test_sonos_controller.py
│   ├── test_nfc_interface.py
│   └── test_app.py
├── docs/
│   └── PLAN.md
└── requirements.txt
```

## .gitignore (minimum)
```
config.json
__pycache__/
*.pyc
*.pyo
.env
```

## NFC Tag Format
Store album ID as plain NDEF text: `apple:{collection_id}`
Example: `apple:1440903625`
- NTAG213 has 144 bytes — plenty for this
- Human-readable, easy to parse

---

## NFC Hardware Contention (Pi)
On the Pi, `player.py` and `app.py` both need the PN532 HAT. Two processes cannot share one SPI device simultaneously.

**Solution:** Stop `player.py` before writing tags, restart it after.
- Phase 5 (before systemd services exist): `pkill -f player.py`
- Phase 6 (after systemd services exist): `sudo systemctl stop vinyl-player`

The web UI settings page should display this reminder when in `pn532` mode. This is a deliberate workflow: the Pi is either playing music or setting up new tags, not both at the same time.

---

## Module Design

### config.json (not committed)
```json
{
  "sn": "3",
  "speaker_ip": "10.0.0.12",
  "nfc_mode": "mock"
}
```

### config.example.json (committed)
```json
{
  "sn": "YOUR_SN_VALUE",
  "speaker_ip": "YOUR_SPEAKER_IP",
  "nfc_mode": "mock"
}
```
`nfc_mode`: `"mock"` on Mac, `"pn532"` on Pi

---

### apple_music.py
- `search_albums(query)` → list of dicts: `{id, name, artist, artwork_url}`
- `get_album_tracks(album_id)` → filter `wrapperType == "track"`, sort by `trackNumber`, apply `upgrade_artwork_url` internally → `[{track_id, name, track_number, artist, album, artwork_url}, ...]`
- `build_track_uri(track_id, sn)` → `x-sonos-http:song:{track_id}.mp4?sid=204&flags=8224&sn={sn}`
- `build_track_metadata(track)` → DIDL-Lite XML string (for Sonos display)
- `upgrade_artwork_url(url)` → replace `100x100bb` with `600x600bb` — called internally by `get_album_tracks`, not by callers

**TDD order:**
1. `test_build_track_uri` — pure function, no I/O, test first
2. `test_build_track_metadata` — pure function, validate XML structure
3. `test_upgrade_artwork_url` — pure string transform
4. `test_search_albums` — mock `urllib.request.urlopen`, test response parsing
5. `test_get_album_tracks` — mock HTTP, verify collection row filtered out, tracks sorted by `trackNumber`, fields mapped correctly, artwork URL upgraded

---

### sonos_controller.py
- `get_speakers()` → list of `{name, ip}` via `soco.discover()`. Note: discovery uses UDP multicast and takes 5–10 seconds.
- `play_album(speaker_ip, track_dicts, sn)` → calls `apple_music.build_track_uri` and `apple_music.build_track_metadata` internally, clears queue, adds all tracks, plays from position 0

**URI building lives in `apple_music.py`. `sonos_controller.play_album` calls those functions — it does not duplicate URI logic.**

**TDD order:**
1. `test_play_album_clears_queue` — mock `soco.SoCo`, verify `clear_queue()` called first
2. `test_play_album_adds_all_tracks` — verify all tracks added in correct order with URIs and metadata
3. `test_play_album_starts_playback` — verify `play_from_queue(0)` called

---

### nfc_interface.py — The Abstraction Layer
Two implementations behind a common interface, plus a standalone `parse_tag_data` function. Both classes are present from the start — `PN532NFC` raises `NotImplementedError` until Phase 5.

**Standalone functions:**
- `parse_tag_data(tag_string)` → parses `apple:{collection_id}` → returns album ID as string. Raises `ValueError` with a clear message if format is unrecognised.

**MockNFC** (Mac testing):
- `read_tag()` → blocks on `input()` waiting for the user to type a tag string. In `--simulate` mode, `read_tag()` is never called.
- `write_tag(data)` → prints what would be written to the tag, returns `True`

**PN532NFC** (Pi with real hardware):
- `read_tag()` → polls Adafruit PN532 library for NDEF tag, returns tag text when detected
- `write_tag(data)` → writes NDEF text record to physical tag
- Both methods raise `NotImplementedError` until implemented in Phase 5

`player.py` imports the correct class based on `nfc_mode` in config.json.

**TDD order:**
1. `test_mock_read_tag` — patch `builtins.input`, verify returned string
2. `test_mock_write_tag` — verify returns `True`, output logged
3. `test_parse_tag_data` — `apple:1440903625` → `"1440903625"`
4. `test_parse_tag_data_invalid` — malformed string raises `ValueError` with clear message

---

### player.py

```
1. Load config.json (always — needed for speaker_ip and sn in all modes)
2. If --simulate <tag_data> flag:
     album_id = parse_tag_data(tag_data)
     tracks = get_album_tracks(album_id)
     play_album(speaker_ip, tracks, sn)
     exit
3. Otherwise:
     instantiate NFC based on nfc_mode
     loop:
       try:
         tag_data = nfc.read_tag()
         album_id = parse_tag_data(tag_data)
         tracks = get_album_tracks(album_id)
         play_album(speaker_ip, tracks, sn)
         log result
       except Exception as e:
         log error, continue loop
```

`--simulate` runs once and exits. The loop catches all exceptions and continues — a bad tag or network error should never crash the player.

**Terminal integration testing (Mac):**
```bash
# Runs once with simulated tag data and exits
python3 player.py --simulate apple:1440903625

# Interactive loop — type tag string at prompt, press Enter to trigger playback
python3 player.py
```

---

### app.py (Flask)
The web UI is purely for searching albums and writing tags. It does not trigger playback.

**Config path:** `app.py` defines a module-level constant:
```python
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
```
All config reads/writes use `CONFIG_PATH`. Tests monkeypatch this constant to a temp file path so the real `config.json` is never touched during testing.

**How to run:**
```bash
# Mac — binds to localhost only
python3 app.py

# Pi — binds to all interfaces, accessible from Mac browser at http://vinyl-pi.local:5000
python3 app.py --host 0.0.0.0
```
`app.py` implements argument parsing for `--host` (default `127.0.0.1`) and passes it to `app.run()`.

**Routes:**
| Route | Method | Body | Purpose |
|---|---|---|---|
| `/` | GET | — | Search page |
| `/search` | GET `?q=` | — | JSON album results (AJAX) |
| `/album/<id>` | GET | — | Album detail — `id` is iTunes `collectionId` |
| `/write-tag` | POST | JSON `{"album_id": "1440903625"}` | Builds `apple:{album_id}`, calls `nfc.write_tag()` |
| `/settings` | GET | — | Settings form |
| `/settings` | POST | Form data: `sn`, `speaker_ip`, `nfc_mode` | Saves fields to `config.json` via `CONFIG_PATH` |
| `/speakers` | GET | — | JSON list of Sonos speakers (5–10s, uses soco.discover()) |

**`/write-tag`** parses body with `request.get_json()`.
**`/settings` POST** reads fields with `request.form.get('sn')` etc.

**TDD order:**
1. `test_search_returns_json` — mock `apple_music.search_albums`, verify response shape
2. `test_album_detail_renders` — mock `apple_music.get_album_tracks`, verify template renders
3. `test_write_tag_mock_mode` — POST JSON `{"album_id": "1440903625"}`, verify `nfc.write_tag` called with `apple:1440903625`
4. `test_settings_saves_config` — monkeypatch `app.CONFIG_PATH` to `tmp_path / "config.json"`, POST form data, verify file written correctly

---

### templates/index.html
- Search bar with AJAX results as you type
- Results: album art, artist, album name, year — clickable

### templates/album.html
- Large album art + track listing
- **"Write to Tag"** button — POSTs JSON `{"album_id": "..."}` to `/write-tag`:
  - Mock mode: shows confirmation with what was "written"
  - Pi mode: writes NDEF to physical tag via PN532 HAT

### templates/settings.html
- Sonos speaker dropdown (populated via AJAX call to `/speakers` on page load — show spinner while loading, takes 5–10 seconds)
- `sn` value field
- NFC mode toggle (mock / pn532)
- Save button — submits as HTML form POST
- In `pn532` mode: reminder banner — "Stop the player before writing tags"

---

## DIDL-Lite Metadata
Pass when queuing each track so Sonos displays track info:
```xml
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
           xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
           xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
           xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
  <item id="-1" parentID="-1" restricted="true">
    <dc:title>{track_name}</dc:title>
    <upnp:class>object.item.audioItem.musicTrack</upnp:class>
    <dc:creator>{artist}</dc:creator>
    <upnp:album>{album_name}</upnp:album>
    <upnp:albumArtURI>{artwork_url}</upnp:albumArtURI>
  </item>
</DIDL-Lite>
```

---

## conftest.py — Key Fixtures

```python
import json
import pytest
from unittest.mock import MagicMock


# --- iTunes API sample data ---

SAMPLE_SEARCH_RESPONSE = {
    "resultCount": 1,
    "results": [
        {
            "wrapperType": "collection",
            "collectionId": 1440903625,
            "collectionName": "Hysteria",
            "artistName": "Def Leppard",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        }
    ],
}

# Note: first item is the album row (wrapperType "collection") — must be filtered out
SAMPLE_LOOKUP_RESPONSE = {
    "resultCount": 3,
    "results": [
        {
            "wrapperType": "collection",
            "collectionId": 1440903625,
            "collectionName": "Hysteria",
            "artistName": "Def Leppard",
        },
        {
            "wrapperType": "track",
            "trackId": 1440904001,
            "trackName": "Women",
            "trackNumber": 1,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
        {
            "wrapperType": "track",
            "trackId": 1440904002,
            "trackName": "Rocket",
            "trackNumber": 2,
            "artistName": "Def Leppard",
            "collectionName": "Hysteria",
            "artworkUrl100": "https://example.com/100x100bb.jpg",
        },
    ],
}


# --- Mock SoCo speaker ---

@pytest.fixture
def mock_speaker(mocker):
    speaker = MagicMock()
    mocker.patch("soco.SoCo", return_value=speaker)
    return speaker


# --- Flask test client ---

@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# --- Temp config file ---

@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({
        "sn": "3",
        "speaker_ip": "10.0.0.12",
        "nfc_mode": "mock"
    }))
    import app
    monkeypatch.setattr(app, "CONFIG_PATH", str(config_file))
    return config_file
```

---

## systemd Service Files (Phase 6)

> **Note:** Replace `pi` in paths with the username you set during Raspberry Pi Imager setup.

**`/etc/systemd/system/vinyl-player.service`**
```ini
[Unit]
Description=Vinyl Emulator NFC Player
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/vinyl-emulator/player.py
WorkingDirectory=/home/pi/vinyl-emulator
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/vinyl-web.service`**
```ini
[Unit]
Description=Vinyl Emulator Web UI
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/vinyl-emulator/app.py --host 0.0.0.0
WorkingDirectory=/home/pi/vinyl-emulator
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

---

## Build Order

### Phase 1 — Core Playback with TDD (Mac)
1. Create `config.json`, `config.example.json`, `.gitignore`, `README.md`
2. `tests/conftest.py` — shared fixtures (see conftest section above)
3. Write tests for `apple_music.py` → implement → pass
4. Write tests for `sonos_controller.py` → implement → pass
5. **Verify:** `python3 -m pytest tests/` — all green
6. **Integration verify (manual terminal test):**
   ```bash
   python3 -c "
   import json
   from apple_music import get_album_tracks
   from sonos_controller import play_album
   config = json.load(open('config.json'))
   tracks = get_album_tracks(1440903625)
   play_album(config['speaker_ip'], tracks, config['sn'])
   "
   ```
   Confirm Hysteria plays on Family Room with track names + art in Sonos app.

### Phase 2 — NFC Interface with TDD (Mac)
7. Write tests for `nfc_interface.py` (MockNFC + `parse_tag_data`) → implement → pass
8. Add `PN532NFC` stub with both methods raising `NotImplementedError`
9. `player.py` — config loading, `--simulate` flag (runs once, exits), main loop with exception handling
10. **Verify:** `python3 player.py --simulate apple:1440903625` → music plays, process exits
11. **Verify loop:** `python3 player.py` → type `apple:1440903625` at prompt → music plays

### Phase 3 — Web UI with TDD (Mac)
12. Write tests for `app.py` routes → implement → pass
13. `templates/` — search, album detail, settings pages
14. **Verify:** Browser at `http://localhost:5000` — search album, view tracks, write tag (mock prints NDEF string to terminal)

### Phase 4 — Hardware Procurement & Pi Setup
**Shopping List:**
| Item | Notes | Est. Cost |
|---|---|---|
| Waveshare PN532 NFC HAT | GPIO, fits Pi Zero W directly, use SPI mode | ~$18 |
| NTAG213 NFC cards (card stock) | Card-sized, printable — not stickers | ~$12 for 20 |
| Micro SD card 16GB+ | New card — keeps Homebridge intact on existing card | ~$10 |

**Pi Setup:**
1. Download Raspberry Pi Imager on Mac
2. Flash new SD card: **Raspberry Pi OS Lite (64-bit)**
3. In Imager settings before flashing: set username + password, hostname `vinyl-pi`, enable SSH, set WiFi credentials — **note the username you choose, it goes into service file paths**
4. Insert card in Pi, power on, wait 60s
5. `ssh YOUR_USERNAME@vinyl-pi.local` from Mac
6. `sudo apt update && sudo apt upgrade -y`
7. `sudo apt install python3-pip python3-dev git -y`
8. `sudo raspi-config` → Interface Options → SPI → Enable → reboot

**PN532 HAT:**
1. Power off Pi
2. Press HAT onto 40-pin GPIO header
3. Set jumpers to SPI mode (per [Waveshare PN532 HAT Wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT))
4. Power on, SSH in
5. `pip3 install adafruit-circuitpython-pn532 RPi.GPIO spidev`
6. Run Adafruit test script to confirm HAT detected

### Phase 5 — Deploy to Pi & Real NFC
1. Push project to GitHub from Mac
2. On Pi — clone the repo:
   - Public: `git clone https://github.com/YOUR_USERNAME/vinyl-emulator.git`
   - Private: `ssh-keygen` on Pi, add public key to GitHub → Settings → SSH Keys, then `git clone git@github.com:YOUR_USERNAME/vinyl-emulator.git`
3. `cd vinyl-emulator && pip3 install -r requirements.txt`
4. `pip3 install adafruit-circuitpython-pn532 RPi.GPIO spidev`
5. `cp config.example.json config.json` then edit with real values (`nfc_mode: "pn532"`)
6. Implement `PN532NFC` in `nfc_interface.py`:
   - Key Adafruit API calls: `pn532.read_passive_target(timeout=0.5)` for reading, `pn532.ntag2xx_write_block()` for writing
   - Reference: https://docs.circuitpython.org/projects/pn532/en/latest/
7. Make sure player is not running: `pkill -f player.py`
8. Test tag writing: `python3 app.py --host 0.0.0.0` → open `http://vinyl-pi.local:5000` → write tag
9. Test tag reading: `python3 player.py` → place tag → music plays

### Phase 6 — Production
1. Create service files at `/etc/systemd/system/` (see systemd section — update paths with your username)
2. `sudo systemctl daemon-reload`
3. `sudo systemctl enable vinyl-player vinyl-web`
4. `sudo systemctl start vinyl-player vinyl-web`
5. **Verify:** Reboot Pi → tag scan → music plays with no manual steps
6. To write new tags after production: `sudo systemctl stop vinyl-player` → write tags → `sudo systemctl start vinyl-player`

---

## requirements.txt
```
soco
flask
requests
pytest
pytest-mock
# Pi only — install separately on Pi after cloning:
# pip3 install adafruit-circuitpython-pn532 RPi.GPIO spidev
```

## Verification Checkpoints
| Phase | Test |
|---|---|
| 1 | `pytest tests/` green; Hysteria plays with track names + art in Sonos app |
| 2 | `--simulate` plays and exits; interactive loop responds to typed tag |
| 3 | Browser search works; album detail renders; mock write prints NDEF to terminal |
| 4 | `ssh vinyl-pi.local` works; PN532 HAT detected without errors |
| 5 | Write tag via UI → scan tag → music plays on Pi |
| 6 | Reboot Pi → scan tag → music plays, no manual steps |
