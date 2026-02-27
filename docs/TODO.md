# Vinyl Emulator — TODO / Backlog

## CI / GitHub Actions

- [ ] **Add GitHub Actions workflow** — run `pytest` on every push and pull request
  - File: `.github/workflows/tests.yml`
  - Trigger: `push` and `pull_request` on `main`
  - Steps: checkout → set up Python 3.11 → `pip install -r requirements.txt` → `python -m pytest tests/ -v`
  - Badge in README

## Packaging / Dependencies

- [ ] **Audit `requirements.txt`** — confirm all packages are listed; add `pytest-mock` if missing
- [ ] **Pin dependency versions** — add version constraints (e.g. `soco>=0.30`, `flask>=3.0`) so the Pi install is reproducible
- [ ] **Create `pyproject.toml`** — optional, but enables `pip install -e .` for development; simplifies adding scripts entry points (`vinyl-player`, `vinyl-web`)

## Hardware (Phase 4)

- [ ] **Purchase hardware** — Raspberry Pi Zero 2 W (with headers), Waveshare PN532 NFC HAT, NTAG213 cards, SD card, USB-C power supply (~$60–75 total, see PLAN.md)
- [ ] **Flash Raspberry Pi OS Lite** — hostname `vinyl-pi`, enable SSH + SPI during imaging
- [ ] **Verify PN532 HAT detects** — run Adafruit test script after hardware assembly

## Pi Deployment (Phase 5)

- [ ] **Implement `PN532NFC.read_tag()`** in `nfc_interface.py` — use `adafruit_pn532`, poll for NDEF text record
- [ ] **Implement `PN532NFC.write_tag()`** in `nfc_interface.py` — write NDEF text record to NTAG213
- [ ] **End-to-end test on Pi** — write tag via web UI, scan tag, music plays
- [ ] **Ensure `config.json` is in `.gitignore`** (already is — double-check after clone on Pi)

## Production (Phase 6)

- [ ] **Create systemd service files** — `vinyl-player.service` and `vinyl-web.service` (see PLAN.md for content)
- [ ] **Enable services on boot** — `sudo systemctl enable vinyl-player vinyl-web`
- [ ] **Reboot test** — tap tag after cold boot, music plays without SSH

## Enhancements

- [ ] **Settings page: Discover button** — currently `/speakers` is called automatically; add a manual "Discover Speakers" button so the 5–10 second scan only runs on request
- [ ] **Player process management from web UI** — on Pi/pn532 mode, Settings page could show a "Stop Player / Start Player" button pair (calls `systemctl stop/start vinyl-player` via subprocess)
- [ ] **iPhone NFC shortcut sticker** — write `http://vinyl-pi.local:5000` as a URL NDEF record on a spare sticker and affix to the Pi enclosure; tapping with iPhone opens the web UI directly
- [ ] **mDNS / hostname verification** — confirm `vinyl-pi.local` resolves from Mac and iPhone once Pi is running
- [ ] **Error page for unknown album/track IDs** — `/album/<id>` and `/track/<id>` currently render blank if iTunes returns nothing; add a friendly 404 response
- [ ] **`--read` output improvement** — `player.py --read` currently prints raw tag string; optionally pretty-print the parsed type and ID
