# Vinyl Emulator — TODO / Backlog

## Packaging / Dependencies

- [ ] **Create `pyproject.toml`** — optional; enables `pip install -e .` and scripts entry points

## Hardware (Phase 4)

- [ ] **Verify PN532 HAT detects** — run Adafruit test script after NFC HAT arrives

## Pi Deployment (Phase 5)

- [ ] **End-to-end test on Pi** — write tag via web UI, scan tag, music plays

## Production (Phase 6)

- [ ] **Reboot test** — tap tag after cold boot, music plays without SSH

## Enhancements

- [ ] **Port 80** — serve on `http://vinyl-pi.local` instead of `http://vinyl-pi.local:5000` using authbind or nginx
- [ ] **mDNS verification** — confirm `vinyl-pi.local` resolves from Mac and iPhone once Pi is on network
