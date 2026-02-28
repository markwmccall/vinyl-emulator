# Vinyl Emulator — TODO / Backlog

## 🔴 Top Priority

- [ ] **In-app update system** — Settings page shows current version (`VERSION` constant in `app.py`) and latest GitHub release. If a newer version is available, shows a banner with a one-click "Update" button. Clicking it runs `git pull` + `pip3 install -r requirements.txt` + restarts both systemd services — no SSH required.
  - Add `VERSION = "0.9.0"` to `app.py`, expose via `/health` response
  - Add `/update/check` route — hits GitHub releases API, caches result 24h in memory, returns `{"current": "0.9.0", "latest": "1.0.0", "update_available": true}`
  - Add `/update/apply` POST route — runs the update sequence with automatic rollback on failure (see below)
  - Settings page: show version in footer, update banner when available
  - Only show update controls in `pn532` mode (on Pi); mock mode shows version only

- [ ] **Update rollback / safety net** — if the update causes `vinyl-web` to fail, the Pi becomes unreachable (bricked) without SSH. Mitigate with:
  - Before updating: record current commit hash (`git rev-parse HEAD`) and write to `.update-rollback`
  - Update sequence with error checking at each step:
    1. `git pull` → if fails, abort (nothing changed)
    2. `pip3 install -r requirements.txt` → if fails, `git reset --hard <prev-commit>`, abort
    3. `systemctl restart vinyl-web vinyl-player`
    4. Health check — poll `GET /health` for up to 15s after restart
    5. If health check fails → `git reset --hard <prev-commit>`, `pip3 install`, restart services again
  - `/update/rollback` POST route — manually revert to saved commit (escape hatch if auto-rollback also fails to reach the health check)
  - Log all steps and outcome to a file (`update.log`) so failures are diagnosable

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
