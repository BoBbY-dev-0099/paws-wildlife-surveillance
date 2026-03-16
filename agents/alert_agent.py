"""
alert_agent.py — Real implementations for ntfy.sh and Telegram alerts,
plus community mesh cascade notifications.
"""
import json
import base64
from typing import Optional
import httpx
from config import NTFY_BASE_URL, NTFY_TOPIC, TELEGRAM_BOT_TOKEN, PUBLIC_BASE_URL


# ── ntfy.sh push notification ────────────────────────────────────────────────

def send_ntfy_alert(
    incident_id: int,
    animal: str,
    severity: int,
    behavior: str,
    translations: dict,
    language: str = "en",
    image_b64: Optional[str] = None,
) -> dict:
    """Send ntfy.sh push notification with localized message."""
    alert_text = translations.get(language, translations.get("en", f"⚠️ {animal} detected"))
    title = f"PAWS Alert — {animal.title()} (Sev {severity}/10)"

    headers = {
        "Title": title,
        "Priority": "urgent" if severity >= 7 else "high",
        "Tags": "rotating_light,wolf" if severity >= 7 else "warning",
        "Click": f"{PUBLIC_BASE_URL}/api/incidents/{incident_id}/report",
    }

    try:
        # Ensure all headers are properly UTF-8 encoded
        # ntfy.sh accepts UTF-8 in headers
        headers_utf8 = {}
        for key, value in headers.items():
            # Replace em dash and other special chars with ASCII equivalents
            value_clean = str(value).replace('—', '-').replace('–', '-')
            headers_utf8[key] = value_clean
        
        # Ensure alert text is UTF-8 encoded
        alert_text_clean = alert_text.replace('—', '-').replace('–', '-')
        
        resp = httpx.post(
            f"{NTFY_BASE_URL}/{NTFY_TOPIC}",
            data=alert_text_clean.encode("utf-8"),
            headers=headers_utf8,
            timeout=10,
        )
        return {"ntfy": "sent", "status_code": resp.status_code, "topic": NTFY_TOPIC}
    except Exception as e:
        print(f"[AlertAgent] ntfy failed: {e}")
        return {"ntfy": "failed", "error": str(e)}


# ── Telegram bot alert ───────────────────────────────────────────────────────

def send_telegram_alert(
    incident_id: int,
    animal: str,
    severity: int,
    behavior: str,
    region: str,
    image_b64: Optional[str] = None,
) -> dict:
    """Send Telegram message with optional photo and inline feedback buttons."""
    if not TELEGRAM_BOT_TOKEN:
        return {"telegram": "skipped", "reason": "no token configured"}

    # Get all registered chat IDs from a hardcoded env var or stored list
    import os
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    if not chat_ids_raw:
        return {"telegram": "skipped", "reason": "no TELEGRAM_CHAT_IDS configured"}

    chat_ids = [c.strip() for c in chat_ids_raw.split(",") if c.strip()]
    base = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    caption = (
        f"🚨 *PAWS Alert — {animal.title()}*\n"
        f"Severity: `{severity}/10`\n"
        f"Behavior: `{behavior}`\n"
        f"Region: `{region}`\n"
        f"Incident: `#{incident_id}`"
    )

    reply_markup = json.dumps({
        "inline_keyboard": [[
            {"text": "✅ Confirmed threat", "callback_data": f"feedback:{incident_id}:confirmed"},
            {"text": "❌ False positive", "callback_data": f"feedback:{incident_id}:false_positive"}
        ]]
    })

    results = {}
    for chat_id in chat_ids:
        try:
            if image_b64:
                # Send photo with caption
                img_bytes = base64.b64decode(image_b64)
                resp = httpx.post(
                    f"{base}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "Markdown",
                        "reply_markup": reply_markup,
                    },
                    files={"photo": ("detection.jpg", img_bytes, "image/jpeg")},
                    timeout=15,
                )
            else:
                resp = httpx.post(
                    f"{base}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": caption,
                        "parse_mode": "Markdown",
                        "reply_markup": json.loads(reply_markup),
                    },
                    timeout=15,
                )
            results[chat_id] = "sent" if resp.status_code == 200 else f"error:{resp.status_code}"
        except Exception as e:
            results[chat_id] = f"failed:{str(e)[:60]}"

    return {"telegram": results}


# ── Master dispatcher ────────────────────────────────────────────────────────

def dispatch_all_alerts(
    incident_id: int,
    animal: str,
    severity: int,
    behavior: str,
    image_b64: Optional[str],
    translations: dict,
    region: str,
    language: str = "en",
    voice_b64: Optional[str] = None,
) -> dict:
    """
    Dispatches all alert channels: ntfy.sh + Telegram.
    Called from pipeline step 10.
    """
    alerts = {}

    # ntfy.sh
    ntfy_result = send_ntfy_alert(
        incident_id=incident_id,
        animal=animal,
        severity=severity,
        behavior=behavior,
        translations=translations,
        language=language,
        image_b64=image_b64,
    )
    alerts.update(ntfy_result)

    # Telegram
    tg_result = send_telegram_alert(
        incident_id=incident_id,
        animal=animal,
        severity=severity,
        behavior=behavior,
        region=region,
        image_b64=image_b64,
    )
    alerts.update(tg_result)

    return alerts


# ── Community mesh cascade ───────────────────────────────────────────────────

def cascade_neighbor_alerts(
    animal: str,
    severity: int,
    region: str,
    lat: float,
    lon: float,
    radius_km: float = 15,
) -> int:
    """
    Broadcasts high-severity alert to neighboring farms on the PAWS mesh.
    Uses ntfy.sh with a region-specific topic so any farm subscribed
    to  paws-mesh-{region}  receives the broadcast.
    Returns count of topics notified (proxy for neighbors reached).
    """
    mesh_topic = f"paws-mesh-{region}"
    message = (
        f"🌐 PAWS Community Alert: {animal.title()} detected "
        f"within {radius_km}km of you. Severity {severity}/10. "
        f"Secure your perimeter. [GPS approx: {lat:.3f},{lon:.3f}]"
    )

    try:
        resp = httpx.post(
            f"{NTFY_BASE_URL}/{mesh_topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": f"⚠️ Nearby Farm Alert — {animal.title()}",
                "Priority": "high",
                "Tags": "warning,farm",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            # Estimate neighbour count — ntfy returns subscriber count in header
            subscriber_count = int(resp.headers.get("x-subscriber-count", 1))
            print(f"[Mesh] Broadcast to {mesh_topic}: {subscriber_count} subscribers")
            return max(1, subscriber_count)
        else:
            print(f"[Mesh] ntfy cascade failed: {resp.status_code}")
            return 0
    except Exception as e:
        print(f"[Mesh] cascade_neighbor_alerts error: {e}")
        return 0
