# Technical Report: Sonos S2 & Apple Music Integration
**Project:** Vinyl Emulator (NFC-to-Sonos)
**Researcher:** Gemini AI & Mark McCall
**Date:** March 2026

---

## 1. Executive Summary
The goal was to enable a Raspberry Pi (Vinyl Emulator) to search and play Apple Music tracks on Sonos S2 hardware (Move 2, Foyer). Initial attempts to scrape credentials from the speaker's local UPnP/XML endpoints failed due to S2 security redactions. The final solution involves treating the Raspberry Pi as an independent Sonos Music API (SMAPI) client, bypassing the speaker for authentication and search.

## 2. Technical Findings: The "S2 Wall"
Our deep dive into the speaker's `sonos_dump.xml` and UPnP responses revealed:
* **Token Redaction:** Sonos S2 firmware redacts the `token` and `key` for Apple Music. Even though the service is active, the speaker will not share these via local network requests.
* **AppLink Requirement:** Apple Music on Sonos requires a specialized OAuth 2.0 flow called "AppLink." 
* **The "999" Error:** Attempting to query Apple Music with just a Household ID results in a `500 Internal Server Error (SonosError 999)`, indicating that a session-specific login token is mandatory.

## 3. Analysis of "Sonify" Success
The third-party app "Sonify" succeeds where standard scripts fail because:
1. **Cloud-First:** It performs its own SMAPI handshake directly with Apple's servers (`sonos-music.apple.com`).
2. **Persistent Credentials:** It harvests a `token` and `key` once and stores them in the device's secure storage, acting as its own controller rather than relying on the speaker's cached credentials.
3. **Direct Search:** It sends search queries directly to the cloud, which is significantly faster than querying through a Sonos speaker.

## 4. The Final Solution: Zero-Proxy Handshake
To replicate this without a MITM proxy, use the following "Polling Handshake" in your project. This works from a private/local Raspberry Pi because it uses outbound polling rather than inbound webhooks.

### The Handshake Code (Python)
```python
import requests
import time
import webbrowser

HHID = "YOUR_HOUSEHOLD_ID_HERE" # e.g., Sonos_q83...
URL = "[https://sonos-music.apple.com/ws/SonosSoap](https://sonos-music.apple.com/ws/SonosSoap)"

def get_tokens():
    # 1. Start the link process
    body = f"""<s:Envelope xmlns:s="[http://schemas.xmlsoap.org/soap/envelope/](http://schemas.xmlsoap.org/soap/envelope/)" xmlns:ns="[http://www.sonos.com/Services/1.1](http://www.sonos.com/Services/1.1)">
      <s:Body><ns:getAppLink><ns:householdId>{HHID}</ns:householdId></ns:getAppLink></s:Body>
    </s:Envelope>"""
    
    r = requests.post(URL, data=body, headers={"SOAPAction": '"[http://www.sonos.com/Services/1.1#getAppLink](http://www.sonos.com/Services/1.1#getAppLink)"'})
    reg_url = r.text.split('<regUrl>')[1].split('</regUrl>')[0].replace('&amp;', '&')
    link_code = r.text.split('<linkCode>')[1].split('</linkCode>')[0]

    print(f"Log in here: {reg_url}")
    webbrowser.open(reg_url)

    # 2. Poll for the resulting tokens
    poll_body = f"""<s:Envelope xmlns:s="[http://schemas.xmlsoap.org/soap/envelope/](http://schemas.xmlsoap.org/soap/envelope/)" xmlns:ns="[http://www.sonos.com/Services/1.1](http://www.sonos.com/Services/1.1)">
      <s:Body><ns:getDeviceAuthToken><ns:householdId>{HHID}</ns:householdId><ns:linkCode>{link_code}</ns:linkCode></ns:getDeviceAuthToken></s:Body>
    </s:Envelope>"""

    print("Waiting for login completion...")
    while True:
        r = requests.post(URL, data=poll_body, headers={"SOAPAction": '"[http://www.sonos.com/Services/1.1#getDeviceAuthToken](http://www.sonos.com/Services/1.1#getDeviceAuthToken)"'})
        if '<token>' in r.text:
            token = r.text.split('<token>')[1].split('</token>')[0]
            key = r.text.split('<key>')[1].split('</key>')[0]
            print(f"SUCCESS!\nTOKEN: {token}\nKEY: {key}")
            return token, key
        time.sleep(5)