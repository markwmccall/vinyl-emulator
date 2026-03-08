# Vinyl Emulator

<img src="static/logo.svg" width="80" alt="Vinyl Emulator logo">

[![Tests](https://github.com/markwmccall/vinyl-emulator/actions/workflows/tests.yml/badge.svg)](https://github.com/markwmccall/vinyl-emulator/actions/workflows/tests.yml)

Tap an NFC card → an album or song plays on your Sonos speaker.

Inspired by [Mark Hank's Sonos/Spotify Vinyl Emulator](https://www.hackster.io/mark-hank/sonos-spotify-vinyl-emulator-3be63d), this project adapts the concept for **Apple Music** and adds a full web UI for searching, writing, and verifying tags — no terminal required after initial setup.

---

## How it works

Each physical NFC card stores a reference to an album or song. When a card is tapped on the reader, the Raspberry Pi reads it, looks up the tracks via the iTunes API, and queues them on your Sonos speaker.

A web app running on the Pi lets you:
- Search Apple Music for albums or songs
- Write a tag to any NFC card
- Play directly to Sonos from the browser
- Verify what's written on any card

---

## Hardware

| Item |
|------|
| **Raspberry Pi Zero 2 W** (with headers pre-soldered) |
| **Waveshare PN532 NFC HAT** |
| **microSD card** (16 GB+, Class 10) |
| **Raspberry Pi power supply** (5V/2.5A USB-C) |
| **NTAG213 NFC cards or stickers** (25–50 pack) |

> **Tip:** The Pi Zero 2 W often ships without a GPIO header. Order the version with headers pre-soldered, or budget time to solder a 2×20 pin header yourself.

---

## Setup

### 1. Flash the SD card

Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Select **Raspberry Pi OS Lite (64-bit)**. Before writing, open the settings and configure:

- Hostname: anything you like (e.g. `vinyl-pi`) — this becomes `hostname.local` on your network
- Enable SSH
- Set a username and password
- Configure your WiFi network

### 2. Assemble the hardware

Attach the PN532 NFC HAT to the Pi's 40-pin GPIO header. Before powering on, configure the HAT jumpers as described in the [Waveshare PN532 HAT wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT):

1. **Set I2C mode** — set I0 to H and I1 to L using the mode jumper caps.
2. **Connect RSTPDN to D20** — enables software reset of the PN532 after failures.
3. **Connect INT0 to D16** — connects the interrupt pin; avoids I2C clock stretching and prevents the bus hang that otherwise requires a power cycle to recover.

> Steps 2 and 3 are optional per the Waveshare docs but **strongly recommended** — they allow the software to recover from NFC read failures automatically without a power cycle.

Insert the SD card and power on. Wait about 60 seconds, then SSH in:

```bash
ssh your-username@your-hostname.local
```

### 3. Verify the HAT is detected

```bash
sudo i2cdetect -y 1
```

You should see `24` appear at address `0x24`. If nothing appears, check that the HAT is firmly seated and the interface switches are set to I2C.

### 4. Install

```bash
curl -sSL https://raw.githubusercontent.com/markwmccall/vinyl-emulator/main/install.sh | bash
```

This downloads the latest release and runs setup — installs dependencies, enables I2C, creates the config, and installs the `vinyl-web` systemd service. It will prompt you to reboot at the end.

> **Note for Pi Zero 2 W users:** The first run compiles `lxml` from source, which can take 10–20 minutes. This is a one-time cost.

### 5. Configure

After rebooting, open `http://your-hostname.local` in your browser and go to **Settings**. Use the **Discover** button to find your Sonos speaker IP, and the **Detect** button to find your `sn` value automatically.

---

## Updating

Open `http://your-hostname.local` in your browser, go to **Settings → Update**, and click **Update Now**. The app will download and install the latest release and restart itself.

---

## Troubleshooting

**`http://your-hostname.local` doesn't load**
- Check the service is running: `sudo systemctl status vinyl-web`
- Check the Pi is on the network: `ping your-hostname.local`
- Try the IP address directly if mDNS isn't resolving

**HAT not detected**
- Confirm the mode jumpers on the HAT are set to I2C (I0=H, I1=L) — see the [Waveshare PN532 HAT wiki](https://www.waveshare.com/wiki/PN532_NFC_HAT)
- Check the HAT is firmly seated — all 40 pins engaged
- Verify with `sudo i2cdetect -y 1` — PN532 should appear at address `0x24`
- If `i2cdetect` hangs for over a minute and shows nothing at `0x24`, the I2C bus is locked up — power cycle the Pi (unplug and replug power; a reboot alone is not enough)

**NFC reader stops working / requires power cycle to recover**
- This is almost always an I2C bus hang caused by the PN532 clock-stretching the SCL line
- **Fix:** Connect the INT0 jumper to D16 (GPIO16) on the HAT — this switches the reader from clock-stretch polling to interrupt-driven mode and prevents the hang. See step 2 in [Assemble the hardware](#2-assemble-the-hardware) above.
- After updating the firmware, also connect RSTPDN to D20 (GPIO20) so the software can reset the reader automatically without a power cycle
- If the jumpers are already set and the bus is currently hung: power cycle the Pi, then check the jumpers

**Music doesn't play after tapping a card**
- Check `sudo systemctl status vinyl-web` for errors
- Confirm `speaker_ip` and `sn` are set correctly in Settings
- Try Play Now from the web UI to rule out a Sonos configuration issue

**`sn` detection finds nothing**
- You need at least one Apple Music item saved as a Sonos favorite
- Try small values manually: `3` or `5` are common

**Speaker IP keeps changing**
- Handled automatically — the system stores the speaker's room name and rediscovers it if the IP changes

---

## Configuration

Settings are managed through the web UI at `http://your-hostname.local/settings`. The underlying `config.json` file contains:

| Key | Description |
|-----|-------------|
| `speaker_ip` | IP address of your Sonos speaker. Use the **Discover** button to find it. |
| `sn` | Apple Music service number assigned by Sonos. Use the **Detect** button to find it automatically (requires at least one Apple Music favorite saved in the Sonos app). If detection finds nothing, try `3` or `5`. |

---

## Web UI

| Page | Description |
|------|-------------|
| Search | Search albums or songs by name |
| Album / Song | Track listing, Play Now, Write to Tag |
| Verify Tag | Read a card and show what album/song it points to |
| Collection | Browse, sort, and delete written tags |
| Settings | Speaker IP, account number, updates |

---

## iPhone shortcut

Write `http://your-hostname.local` as a URL record on a spare NTAG213 sticker and stick it on the Pi enclosure. Tapping it with an iPhone opens Safari directly to the web UI — no app needed.

---

## Contributing

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Acknowledgements

Concept adapted from [Sonos / Spotify Vinyl Emulator](https://www.hackster.io/mark-hank/sonos-spotify-vinyl-emulator-3be63d) by Mark Hank.
