"""Read the current Sonos queue and show the DIDL desc value for each item."""
import json
import soco
from soco.music_services.accounts import Account

CONFIG_PATH = "config.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

speaker_ip = config["speaker_ip"]
sn = config["sn"]

speaker = soco.SoCo(speaker_ip)
print(f"Connected to: {speaker.player_name} ({speaker_ip})")
print()

# Show accounts on device
print("=== Accounts on device ===")
try:
    accounts = Account.get_accounts(soco=speaker)
    for serial, acc in sorted(accounts.items()):
        print(f"  SerialNum={serial}, Type={acc.service_type}, UN={acc.username!r}, NN={acc.nickname!r}")
except Exception as e:
    print(f"  Error fetching accounts: {e}")
print()

# Show current queue - raw XML + parsed
print("=== Current Queue ===")
response = speaker.contentDirectory.Browse([
    ("ObjectID", "Q:0"),
    ("BrowseFlag", "BrowseDirectChildren"),
    ("Filter", "*"),
    ("StartingIndex", 0),
    ("RequestedCount", 3),
    ("SortCriteria", ""),
])
raw = response.get("Result", "")
print("=== Raw DIDL-Lite (first 3 items) ===")
# Pretty-print by splitting on </item>
parts = raw.split("</item>")
for i, part in enumerate(parts[:3]):
    print(f"\n--- Item {i} ---")
    print(part[:2000] + ("</item>" if i < len(parts)-1 else ""))
