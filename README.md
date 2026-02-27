# Vinyl Emulator

Tap an NFC card → an album or song plays on your Sonos speaker.

Inspired by [Mark Hank's Sonos/Spotify Vinyl Emulator](https://www.hackster.io/mark-hank/sonos-spotify-vinyl-emulator-3be63d), this project adapts the concept for **Apple Music** and adds a full web UI for searching, writing, and verifying tags — no terminal required after initial setup.

---

## How it works

Each physical NFC card stores a short tag string (`apple:1440903625` for an album, `apple:track:1440904001` for a single song). When a card is tapped on the reader, the Raspberry Pi reads the tag, looks up the tracks via the iTunes API, and queues them on your Sonos speaker.

A Flask web app running on the same Pi lets you:
- Search Apple Music for albums or songs
- Write a tag to any NFC card
- Play directly to Sonos from the browser
- Verify what's written on any card

---

## Hardware

| Item | Notes | Approx. Price |
|------|-------|---------------|
| **Raspberry Pi Zero 2 W** (with headers pre-soldered) | Compact, WiFi built-in. Pi 3B+ also works. | $15 |
| **Waveshare PN532 NFC HAT** | Plugs directly onto the Pi GPIO — no wiring needed. Search "Waveshare PN532 NFC HAT Raspberry Pi". | $18–22 |
| **microSD card** (16 GB+, Class 10) | For Raspberry Pi OS Lite (headless) | $8–12 |
| **Raspberry Pi power supply** (5V/2.5A USB-C) | Official Pi supply recommended | $8–12 |
| **NTAG213 NFC cards or stickers** (25–50 pack) | One per album/song. 144-byte capacity is plenty. | $10–15 |

**Total: ~$60–75**

> **Tip:** The Pi Zero 2 W often ships without a GPIO header. Order the version with headers pre-soldered, or budget time to solder a 2×20 pin header yourself.

---

## Raspberry Pi setup

After assembling the hardware and flashing **Raspberry Pi OS Lite (32-bit)** (headless, with SSH and WiFi configured in Raspberry Pi Imager):

```bash
git clone https://github.com/markwmccall/vinyl-emulator.git
cd vinyl-emulator
chmod +x setup.sh && ./setup.sh
```

`setup.sh` does everything in one shot:
- Installs system packages (`python3-pip`, `python3-dev`)
- Enables the SPI interface (required for the PN532 HAT)
- Installs Python dependencies including the Adafruit PN532 library
- Creates `config.json` with `nfc_mode=pn532`
- Installs and enables the `vinyl-player` and `vinyl-web` systemd services

It will prompt you to reboot at the end — SPI requires a reboot to take effect.

After rebooting, open `http://vinyl-pi.local:5000` in your browser, go to **Settings**, and enter your Sonos speaker IP and `sn` value. That's the only manual configuration step.

---

## Mac / development setup

```bash
pip3 install flask soco pytest pytest-mock
cp config.json.example config.json   # set nfc_mode: "mock"
python3 app.py                        # binds to 127.0.0.1:5000
```

---

## Configuration

`config.json` is created by `setup.sh` on the Pi, or manually from `config.json.example` on Mac. It is never committed to git.

| Key | Description |
|-----|-------------|
| `speaker_ip` | IP address of your Sonos speaker. Use the Discover button in Settings to find it. |
| `sn` | Apple Music account serial number used by Sonos. Usually `3` or `5`. Find it in Settings → Discover, or check Sonos favorites that include Apple Music content. |
| `nfc_mode` | `mock` for Mac/dev (reads from stdin), `pn532` for Raspberry Pi with the Waveshare HAT. |

---

## Running

**Web UI:**
```bash
python3 app.py                        # Mac — binds to 127.0.0.1:5000
python3 app.py --host 0.0.0.0         # Pi — accessible from your phone
```

Open `http://localhost:5000` (or `http://vinyl-pi.local:5000` from your phone).

**Player daemon (NFC loop):**
```bash
python3 player.py                            # waits for card taps, plays on Sonos
python3 player.py --simulate apple:1440903625  # play once without a card
python3 player.py --read                     # read one tag, print its content, exit
```

On the Pi with systemd, the player and web UI start automatically on boot. To manage them manually:
```bash
sudo systemctl stop vinyl-player     # stop before writing new tags
sudo systemctl start vinyl-player    # restart after writing tags
sudo systemctl status vinyl-player   # check if running
```

---

## Web UI pages

| Page | URL | Description |
|------|-----|-------------|
| Search | `/` | Search albums or songs by name |
| Album | `/album/{id}` | Track listing, Play Now, Write to Tag |
| Song | `/track/{id}` | Single track, Play Now, Write to Tag |
| Verify Tag | `/verify` | Read a card and show what album/song it points to |
| Settings | `/settings` | Speaker IP, account number, NFC mode |

---

## Tag format

| Tag string | What plays |
|------------|-----------|
| `apple:1440903625` | Full album (collection ID from iTunes) |
| `apple:track:1440904001` | Single song (track ID from iTunes) |

Tags are written as NDEF text records. NTAG213 cards (144 bytes) are more than large enough.

---

## iPhone NFC shortcut

Write `http://vinyl-pi.local:5000` as a URL record on a spare NTAG213 sticker and stick it on the Pi enclosure. Tapping it with an iPhone opens Safari directly to the web UI — no app needed.

---

## Project structure

```
app.py              Flask web app (search, play, write-tag, verify)
player.py           NFC loop daemon + --simulate / --read flags
apple_music.py      iTunes Search API: search albums/songs, fetch tracks
sonos_controller.py Sonos SOAP/UPnP: queue and play tracks via SoCo
nfc_interface.py    NFC abstraction: MockNFC (stdin), PN532NFC (Pi)
setup.sh            One-shot Pi setup script
etc/                systemd service file templates
config.json         Runtime config (speaker IP, sn, NFC mode) — not committed
templates/          Jinja2 HTML templates
static/             CSS
tests/              pytest test suite (81 tests)
docs/PLAN.md        Architecture notes and Sonos SMAPI findings
docs/TODO.md        Backlog
```

---

## Tests

```bash
python -m pytest tests/ -v
```

81 tests covering all modules.

---

## Acknowledgements

Concept adapted from [Sonos / Spotify Vinyl Emulator](https://www.hackster.io/mark-hank/sonos-spotify-vinyl-emulator-3be63d) by Mark Hank.
