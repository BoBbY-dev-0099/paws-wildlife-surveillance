"""
deterrent_agent.py — Sends real HTTP commands to the edge device (e.g. Raspberry Pi)
to trigger ultrasonic emitters, strobe lights, sirens, or predator audio playback.

If EDGE_DEVICE_URL is not configured, falls back to logging only.
"""
import json
import httpx
from config import EDGE_DEVICE_URL

# Deterrent type → GPIO/device command mapping
DETERRENT_COMMANDS = {
    "ultrasonic":      {"command": "ultrasonic", "duration_sec": 10, "frequency_hz": 25000},
    "strobe":          {"command": "strobe",     "duration_sec": 15, "flash_rate_hz": 5},
    "siren":           {"command": "siren",      "duration_sec": 10, "pattern": "wail"},
    "predator_audio":  {"command": "audio",      "duration_sec": 12, "file": "lion_roar.mp3"},
}


def trigger_deterrent(deterrent_type: str) -> bool:
    """
    Sends a deterrent activation command to the edge device via HTTP POST.

    POST {EDGE_DEVICE_URL}/trigger
    Body: {"command": "...", "duration_sec": ..., ...}

    Returns True if the device acknowledged (HTTP 200), False otherwise.
    If EDGE_DEVICE_URL is empty, logs the command and returns True
    (demo mode — assume deterrent fired for hackathon purposes).
    """
    command = DETERRENT_COMMANDS.get(deterrent_type)
    if not command:
        print(f"[Deterrent] Unknown deterrent type '{deterrent_type}' — skipping")
        return False

    if not EDGE_DEVICE_URL:
        print(f"[Deterrent] DEMO MODE — would fire: {json.dumps(command)} "
              f"(set EDGE_DEVICE_URL to connect to real edge device)")
        return True  # pretend it worked for demo

    try:
        resp = httpx.post(
            f"{EDGE_DEVICE_URL}/trigger",
            json=command,
            timeout=8,
        )
        if resp.status_code == 200:
            print(f"[Deterrent] ✅ {deterrent_type} activated. Device response: {resp.text[:80]}")
            return True
        else:
            print(f"[Deterrent] ❌ Device returned {resp.status_code}: {resp.text[:80]}")
            return False
    except httpx.ConnectError:
        print(f"[Deterrent] ❌ Cannot reach edge device at {EDGE_DEVICE_URL} — check network")
        return False
    except Exception as e:
        print(f"[Deterrent] ❌ trigger_deterrent error: {e}")
        return False
