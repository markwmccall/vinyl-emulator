# Vinyl Emulator — TODO / Backlog

## 🔴 Top Priority

- [ ] **In-app update system** — Settings page shows current version (`VERSION` constant in `app.py`) and latest GitHub release. If a newer version is available, shows a banner with a one-click "Update" button. Clicking it runs `git pull` + `pip3 install -r requirements.txt` + restarts both systemd services — no SSH required.
  - Add `VERSION = "0.9.0"` to `app.py`, expose via `/health` response
  - Add `packaging>=24.0` to `requirements.txt` — use `packaging.version.Version` for safe semver comparison (plain string compare fails for e.g. `"0.10.0" > "0.9.0"`)
  - Add `/update/check` route — hits GitHub releases API (no auth needed for public repos), caches result 24h in a module-level dict, returns `{"current": "0.9.0", "latest": "1.0.0", "update_available": true}`
    - GitHub API endpoint: `https://api.github.com/repos/markwmccall/vinyl-emulator/releases/latest`
    - Response field to read: `tag_name` (e.g. `"v1.0.0"`) — strip leading `v` before comparing
  - Add `/update/apply` POST route — **must be async**: spawn a background `threading.Thread`, return `{"status": "started"}` immediately (the thread restarts the very server handling this request, so it cannot block)
  - Add `/update/status` GET route — returns current state of the background update: `{"state": "idle"|"running"|"success"|"failed"|"rolled_back", "log": "...last N lines of update.log..."}`
  - Settings page: show version in footer; poll `/update/status` every 2s while update is running; show result when done
  - Only show update controls in `pn532` mode (on Pi); mock mode shows version only
  - Add `.update-rollback` and `update.log` to `.gitignore`

- [ ] **Update rollback / safety net** — if the update causes `vinyl-web` to fail, the Pi becomes unreachable (bricked) without SSH. Mitigate with:
  - Before updating: record current commit hash (`git rev-parse HEAD`) and write to `.update-rollback`
  - Update sequence (runs in background thread) with error checking at each step:
    1. `git pull` → if fails, abort (nothing changed)
    2. `pip3 install --break-system-packages -r requirements.txt` → if fails, `git reset --hard <prev-commit>`, abort
    3. `sudo systemctl restart vinyl-web vinyl-player`
    4. Health check — poll `GET http://localhost:5000/health` (from within the same thread) for up to 15s after restart
    5. If health check fails → `git reset --hard <prev-commit>`, re-run pip install, restart services again
  - `/update/rollback` POST route — manually revert to commit saved in `.update-rollback` (escape hatch if auto-rollback also fails to reach the health check)
  - All steps append to `update.log` with timestamps; `/update/status` exposes last 20 lines

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
