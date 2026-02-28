# Vinyl Emulator — TODO / Backlog

## Housekeeping

- [x] Remove unused files
- [x] Code review — all production modules
- [x] Add MIT license
- [x] Enable Dependabot alerts
- [x] Branch protection on main

## CI / GitHub Actions

- [x] GitHub Actions workflow — pytest on push/PR with badge in README

## Packaging / Dependencies

- [x] Pin dependency versions in `requirements.txt`
- [ ] **Create `pyproject.toml`** — optional; enables `pip install -e .` and scripts entry points

## Hardware (Phase 4)

- [x] Purchase hardware — Pi Zero 2 W, Waveshare PN532 NFC HAT, NTAG213 cards, SD card, power supply
- [x] Flash Raspberry Pi OS Lite — hostname `vinyl-pi`, SSH + SPI enabled
- [ ] **Verify PN532 HAT detects** — run Adafruit test script after NFC HAT arrives

## Pi Deployment (Phase 5)

- [ ] **Implement `PN532NFC.read_tag()`** — use `adafruit_pn532`, poll for NDEF text record
- [ ] **Implement `PN532NFC.write_tag()`** — write NDEF text record to NTAG213
- [ ] **Implement `PN532NFC.write_url_tag()`** — write URL NDEF record to NTAG213
- [ ] **End-to-end test on Pi** — write tag via web UI, scan tag, music plays

## Production (Phase 6)

- [x] systemd service files (`etc/vinyl-player.service`, `etc/vinyl-web.service`)
- [x] `setup.sh` — one-shot Pi setup script
- [ ] **Reboot test** — tap tag after cold boot, music plays without SSH

## Enhancements

- [ ] **Port 80** — serve on `http://vinyl-pi.local` instead of `http://vinyl-pi.local:5000` using authbind or nginx
- [x] Player process management from web UI (Settings page — pn532 mode only)
- [x] iPhone NFC sticker — write URL tag from Settings page
- [ ] **mDNS verification** — confirm `vinyl-pi.local` resolves from Mac and iPhone once Pi is on network
