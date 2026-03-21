import os
import sys
import time
import threading
import json
import subprocess
import re
import traceback
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

# Add parent directory to path so we can import agents/
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
import requests
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
import asyncio
import httpx

from dotenv import load_dotenv
try:
    from ultralytics import YOLO
except (ImportError, OSError):
    print("⚠️  Warning: ultralytics (YOLO) not found or failed to load (possibly torch DLL error). Local inference will be disabled.")
    YOLO = None


from backend_fastapi.stream_manager import load_streams, add_stream, update_stream, delete_stream, get_stream_by_id


# -----------------------------
# SSE Manager for Real-time Updates
# -----------------------------
# Import the SSE manager used by the pipeline
from backend_fastapi.sse import nova_sse
from backend_fastapi.yt_resolver import is_youtube, resolve_youtube_to_direct_url



# -----------------------------
# Paths + ENV
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environments immediately
load_dotenv(ENV_PATH)
load_dotenv(BASE_DIR.parent / ".env")

print(f"✅ main.py loaded from: {BASE_DIR}", flush=True)
print(f"✅ Looking for .env at: {ENV_PATH}", flush=True)

# ─── Cloudflare Tunnel (auto-start for public webhook URL) ───────────────────
# The tunnel makes us reachable from Modal.com cloud so webhooks actually land.

PUBLIC_WEBHOOK_BASE = os.getenv("PUBLIC_WEBHOOK_BASE", "").strip()  # override via env
_tunnel_process = None

def _start_cloudflared_tunnel(local_port: int = 8000) -> str:
    """
    Spin up cloudflared quick tunnel and extract the public HTTPS URL.
    Returns the base public URL string (no trailing slash).
    Falls back to localhost if cloudflared isn't available.
    """
    global _tunnel_process

    # Look for cloudflared one level up from here (project root)
    cloudflared_candidates = [
        BASE_DIR.parent / "cloudflared.exe",
        BASE_DIR.parent.parent / "cloudflared.exe",
        Path("cloudflared.exe"),
        Path("cloudflared"),
    ]
    cf_path = next((p for p in cloudflared_candidates if p.exists()), None)

    if not cf_path:
        print("⚠️  cloudflared not found — webhook will use localhost (Modal won't reach it!)")
        return f"http://localhost:{local_port}"

    tunnel_log = BASE_DIR / "tunnel_live.log"
    print(f"🌐 Starting cloudflared tunnel via {cf_path}...", flush=True)

    _tunnel_process = subprocess.Popen(
        [str(cf_path), "tunnel", "--url", f"http://localhost:{local_port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    public_url: Optional[str] = None
    deadline = time.time() + 20  # wait up to 20s

    assert _tunnel_process.stdout is not None  # Popen with PIPE always has stdout
    for line in _tunnel_process.stdout:
        line = line.strip()
        # Echo to terminal so user can see
        print(f"  [tunnel] {line}", flush=True)
        with open(tunnel_log, "a") as f:
            f.write(line + "\n")

        # Try to capture the URL
        m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
        if m:
            public_url = m.group(0).rstrip("/")
            print(f"✅ Public tunnel URL: {public_url}", flush=True)
            break

        if time.time() > deadline:
            print("⚠️  Timed out waiting for tunnel URL", flush=True)
            break

    # Keep consuming stdout in background so process doesn't block
    def _drain():
        assert _tunnel_process is not None and _tunnel_process.stdout is not None
        for _line in _tunnel_process.stdout:
            pass

    threading.Thread(target=_drain, daemon=True).start()

    return public_url if public_url else f"http://localhost:{local_port}"

# Resolve public URL at import time
def get_public_url():
    global PUBLIC_WEBHOOK_BASE
    if not PUBLIC_WEBHOOK_BASE or "localhost" in PUBLIC_WEBHOOK_BASE:
        PUBLIC_WEBHOOK_BASE = _start_cloudflared_tunnel(local_port=8000)
    return PUBLIC_WEBHOOK_BASE

get_public_url()
print(f"🔗 Webhook base URL: {PUBLIC_WEBHOOK_BASE}", flush=True)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1").strip()

print("✅ AWS_DEFAULT_REGION:", AWS_DEFAULT_REGION, flush=True)
print("✅ AWS_ACCESS_KEY_ID present:", bool(AWS_ACCESS_KEY_ID), flush=True)
print("✅ AWS_SECRET_ACCESS_KEY present:", bool(AWS_SECRET_ACCESS_KEY), flush=True)

# ✅ Free Push Notifications via ntfy.sh (No Auth Required for Hackathons!)
# Download the 'ntfy' app on iOS/Android and subscribe to this topic name:
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "farmguard_nova_alerts_xyz89")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
print(f"✅ Push Notifications Topic: ntfy.sh/{NTFY_TOPIC}", flush=True)
print(f"✅ Telegram Bot Token present: {bool(TELEGRAM_BOT_TOKEN)}", flush=True)

def set_telegram_webhook(public_url: str):
    """
    Registers the backend's public tunnel URL with Telegram
    so callback queries land on our /webhook/telegram endpoint.
    Includes a retry loop because new tunnels take a few seconds to propagate.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  No TELEGRAM_BOT_TOKEN, skipping webhook registration.")
        return
    
    webhook_url = f"{public_url}/webhook/telegram"
    print(f"🤖 Preparing to register Telegram webhook: {webhook_url}...")
    
    # Give the tunnel 5 seconds to "warm up" and propagate DNS
    time.sleep(5)
    
    for attempt in range(1, 4):
        try:
            print(f"🤖 Registering Telegram webhook (Attempt {attempt}/3)...")
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                data={"url": webhook_url},
                timeout=10
            )
            if resp.status_code == 200:
                print("✅ Telegram webhook registered successfully.")
                return
            else:
                print(f"⚠️  Attempt {attempt} failed: {resp.status_code} {resp.text}")
                if attempt < 3:
                    print(f"⏳ Retrying in 5 seconds...")
                    time.sleep(5)
        except Exception as e:
            print(f"❌ Error during registration attempt {attempt}: {e}")
            if attempt < 3:
                time.sleep(5)
    
    print("❌ Failed to register Telegram webhook after multiple attempts.")

# NOW register Telegram webhook with the loaded token (in background)
if PUBLIC_WEBHOOK_BASE and "localhost" not in PUBLIC_WEBHOOK_BASE:
    threading.Thread(target=set_telegram_webhook, args=(PUBLIC_WEBHOOK_BASE,), daemon=True).start()

def send_push_notification(title: str, message: str) -> tuple[bool, str]:
    """
    Sends a completely FREE push notification to your phone!
    Just install 'ntfy' on iOS/Android and subscribe to the NTFY_TOPIC name.
    """
    try:
        resp = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode(encoding='utf-8'),
            headers={
                "Title": title.encode("utf-8"),
                "Priority": "high",
                "Tags": "rotating_light,tiger"
            }
        )
        if resp.status_code == 200:
            return True, "Push notification sent successfully!"
        return False, f"ntfy error: {resp.status_code}"
    except Exception as e:
        return False, f"Request error: {e}"


def is_probably_youtube(url: str) -> bool:
    u = (url or "").lower()
    return ("youtube.com" in u) or ("youtu.be" in u) or ("m.youtube.com" in u)


def resolve_youtube_to_direct_url(url: str) -> str:
    """
    Resolve YouTube URL -> direct playable URL using yt-dlp.
    More robust than best[ext=mp4]/best because it prefers progressive streams when possible.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # Prefer progressive MP4 (audio+video). Fallback to any video stream.
        "format": "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none]",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        direct = info.get("url")
        if direct:
            return direct

        fmts = info.get("formats") or []
        for f in reversed(fmts):
            if f.get("vcodec") == "none":
                continue
            u = f.get("url")
            if u:
                return u

        raise RuntimeError("Could not resolve YouTube URL to a direct stream URL.")


# -----------------------------
# Modal Inference Configuration
# -----------------------------
# -----------------------------
# Configuration
# -----------------------------
MODAL_API_URL = "https://bobrr5219--paws-stream.modal.run"

DANGEROUS = {"elephant", "tiger", "bear"}
DANGEROUS_MIN_CONF = 0.70

COOLDOWN_SECONDS = 900  # 15 minutes
last_alert: Dict[str, float] = {}  # key -> timestamp


def can_send_alert(key: str, cooldown: int = COOLDOWN_SECONDS) -> bool:
    now = time.time()
    prev = last_alert.get(key, 0.0)
    if now - prev >= cooldown:
        last_alert[key] = now
        return True
    return False


app = FastAPI(title="Farm Intrusion Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

GPU_LOCK = asyncio.Lock()
ACTIVE_KEY = None  # stores the active 'source' string


async def claim_gpu(key: str):
    global ACTIVE_KEY

    # If another stream already holds GPU, reject
    if ACTIVE_KEY is not None and ACTIVE_KEY != key:
        raise HTTPException(
            status_code=429,
            detail={"error": "GPU is busy", "active_source": ACTIVE_KEY},
        )

    # If free, claim
    if ACTIVE_KEY is None:
        await GPU_LOCK.acquire()
        ACTIVE_KEY = key


def release_gpu(key: str):
    global ACTIVE_KEY
    if ACTIVE_KEY == key:
        ACTIVE_KEY = None
        if GPU_LOCK.locked():
            GPU_LOCK.release()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


state: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "fps": 0.0,
    "last_detections": [],
    "source": None,
    "phone": None,   # ✅ store the logged-in user's phone (from /start payload)
    "frame_id": 0,
    "ts": 0,
}

cap: Optional[cv2.VideoCapture] = None
worker_thread: Optional[threading.Thread] = None
stop_event = threading.Event()

frame_lock = threading.Lock()
latest_frame: Optional[np.ndarray] = None  # annotated BGR


def open_capture(source: str) -> cv2.VideoCapture:
    """
    Open cv2.VideoCapture from:
    - webcam: "camera:0"
    - direct video url: mp4/m3u8/rtsp/http
    - youtube url: resolve first (best-effort)
    """
    src = (source or "").strip()

    if src.startswith("camera:"):
        idx = int(src.split(":", 1)[1])
        c = cv2.VideoCapture(idx)
    else:
        if is_probably_youtube(src):
            resolved = resolve_youtube_to_direct_url(src)
            print(f"✅ YouTube resolved -> {resolved[:120]}...", flush=True)
            src = resolved

        c = cv2.VideoCapture(src)

    if not c.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")

    # best-effort latency tweak
    c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return c


def close_capture():
    global cap
    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass
    cap = None


# -----------------------------
# Inference Logic Moved to Modal
# -----------------------------

import sqlite3
import base64
from datetime import datetime
from backend_fastapi.nova_agent import analyze_incident_with_nova

def background_nova_alert(frame: np.ndarray, phone: str, label: str, conf: float, image_list: Optional[List[np.ndarray]] = None, source_model: str = "unknown"):
    # Encode frame to jpeg bytes for primary
    ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
    primary_image_bytes = jpg.tobytes() if ok else b""
    
    # Store base64 constraint for the Dashboard UI
    b64_img = base64.b64encode(primary_image_bytes).decode('utf-8') if primary_image_bytes else ""
        
    print(f"🧠 Asking Amazon Nova to analyze {label} ({len(image_list) if image_list else 1} frames)...", flush=True)
    
    # These would normally come from a global config or the payload
    # For now we use defaults or extracted values
    farm_lat = float(os.getenv("FARM_LAT", 27.7))
    farm_lon = float(os.getenv("FARM_LON", 85.3))
    farmer_lang = os.getenv("FARM_LANGUAGE", "en")
    
    # Encode each frame in the image_list to JPEG bytes before passing to Nova
    encoded_frames: List[bytes] = []
    if image_list:
        for f in image_list:
            ok_enc, buf = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if ok_enc:
                encoded_frames.append(buf.tobytes())
    if not encoded_frames:
        encoded_frames = [primary_image_bytes] if primary_image_bytes else []

    nova_result = analyze_incident_with_nova(
        image_bytes=primary_image_bytes, 
        animal_label=label,
        image_list=encoded_frames,
        confidence=conf,
        source_model=source_model,
        farm_lat=farm_lat,
        farm_lon=farm_lon,
        farmer_language=farmer_lang,
        active_threat_classes=list(DANGEROUS)
    )
    
    severity = nova_result.get("severity_score", 0)
    summary = nova_result.get("reasoning", nova_result.get("incident_summary", f"{label} detected."))
    action_en = nova_result.get("farmer_message_en", nova_result.get("recommended_action", "Stay safe."))
    action_np = nova_result.get("farmer_message_local", nova_result.get("nepali_translation", "सुरक्षित रहनुहोस्।"))

    msg = (
        f"🚨 FarmGuard NOVA\n"
        f"Threat Level: {severity}/10\n"
        f"{summary[:150]}...\n\n"
        f"🎯 {action_np}\n"
    )
    
    # Save to Django SQLite DB natively
    db_path = BASE_DIR.parent / "db.sqlite3"
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("""
            INSERT INTO core_incident (
                user_phone, timestamp, animal_type, confidence, 
                nova_summary, nova_severity, recommended_action, 
                nepali_translation, image_base64, resolved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            phone or "unknown", now_str, label, float(conf),
            summary, int(severity), action_en, action_np, b64_img, False
        ))
        conn.commit()
        conn.close()
        print(f"✅ Incident saved to SQLite Database.")
        
        # Broadcast the Nova result to all SSE clients
        nova_sse.publish({
            "step": "nova_analysis",
            "message": "Nova analysis received",
            "data": {
                "incident_id": phone,
                "severity_score": int(severity),
                "reasoning": summary,
                "recommended_action": action_en,
                "nepali_translation": action_np
            }
        })
    except Exception as e:
        print(f"❌ Failed to save incident to SQLite: {e}")
    
    ok_push, info = send_push_notification(f"🚨 Nova Alert: {label.title()}", msg)
    if ok_push:
        print(f"✅ Push Notification Sent: {info}", flush=True)
    else:
        print(f"❌ Push Notification Failed: {info}", flush=True)


def maybe_send_sns_alert(detections: List[Dict[str, Any]], frame: np.ndarray):
    """
    Sends SMS alert ONLY to the phone stored in state["phone"] (the user who started detection).
    Uses cooldown to prevent spam.
    """
    if not detections:
        return

    # Phone isn't strictly required for global push, but good for logs
    phone = state.get("phone")
    if not NTFY_TOPIC:
        return

    for d in detections:
        label = (d.get("label") or "").lower().strip()
        conf = float(d.get("confidence") or 0)

        if label in DANGEROUS and conf >= DANGEROUS_MIN_CONF:
            if not can_send_alert(label):
                print(f"⏳ Cooldown active for {label}. No SMS.", flush=True)
                continue

            # Spin off Nova reasoning thread so we don't block YOLO camera feed
            threading.Thread(
                target=background_nova_alert,
                args=(frame.copy(), phone, label, conf, [frame.copy()], "local-yolo"),
                daemon=True
            ).start()


@app.post("/start")
async def start_detection(payload: Dict[str, Any] = Body(default={})):
    global worker_thread, cap

    source = (payload.get("source") or "camera:0").strip()
    phone = (payload.get("phone") or "").strip()

    # ✅ store user's phone for this session (only this phone gets SMS)
    state["phone"] = phone or None

    # ✅ enforce single-user GPU
    await claim_gpu(source)

    # If already running, just return (GPU already claimed by same source)
    if state["running"]:
        return {"ok": True, "running": True, "message": "Already running", "source": state["source"]}

    stop_event.clear()
    state["running"] = True
    state["started_at"] = time.time()
    state["last_detections"] = []
    state["source"] = source
    state["frame_id"] = 0
    state["ts"] = int(time.time() * 1000)

    # Note: Worker Thread for local detection was completely removed.
    # Modal now handles the inference loop autonomously.

    return {"ok": True, "running": True, "source": source}


@app.post("/stop")
async def stop_detection():
    if not state["running"]:
        # ensure GPU is released if something got stuck
        key = state.get("source")
        if key:
            release_gpu(key)
        return {"ok": True, "running": False, "message": "Already stopped"}

    state["running"] = False
    stop_event.set()

    key = state.get("source")
    if key:
        release_gpu(key)

    return {"ok": True, "running": False}


@app.get("/status")
def status():
    return {
        "running": state["running"],
        "fps": round(state["fps"], 2),
        "source": state["source"],
        "phone": state["phone"],
        "frame_id": state["frame_id"],
        "ts": state["ts"],
        "push_topic": NTFY_TOPIC,
        "dangerous": list(DANGEROUS),
        "dangerous_min_conf": DANGEROUS_MIN_CONF,
        "cooldown_seconds": COOLDOWN_SECONDS,
    }


@app.get("/latest")
def latest():
    return JSONResponse({
        "running": state["running"],
        "fps": round(state["fps"], 2),
        "detections": state["last_detections"],
        "source": state["source"],
        "frame_id": state["frame_id"],
        "ts": state["ts"],
    })


@app.post("/detect_image_json")
def detect_image_json():
    return JSONResponse({"ok": False, "error": "Deprecated in favor of Modal stream"}, status_code=400)


@app.post("/detect_image_render")
def detect_image_render():
    return JSONResponse({"ok": False, "error": "Deprecated in favor of Modal stream"}, status_code=400)

@app.get("/")
def root():
    return {"status": "FastAPI Webhook & Proxy Receiver", "running": state["running"]}


# -----------------------------
# SSE and Incidents Endpoints
# -----------------------------

# In-memory storage for incidents (temporary - replace with DB later)
incidents_db = []

@app.get("/api/incidents")
def get_incidents(limit: int = 50):
    """Get all incidents from database"""
    from models.incident import SessionLocal, Incident
    
    db = SessionLocal()
    try:
        incidents = db.query(Incident).order_by(
            Incident.created_at.desc()
        ).limit(limit).all()
        
        result = []
        for inc in incidents:
            result.append({
                "id": inc.id,
                "camera_id": inc.camera_id,
                "animal": inc.animal,
                "confidence": inc.confidence,
                "severity_score": inc.nova_severity or 0,
                "timestamp": inc.created_at.isoformat() + "Z" if inc.created_at else None,
                "behavior": inc.nova_behavior or "unknown",
                "location": f"Camera {inc.camera_id}",
                "status": inc.status,
                "region": inc.region,
                "nova_analysis": {
                    "reasoning": inc.nova_reasoning,
                    "behavior_description": inc.nova_behavior_description,
                    "animal_count": inc.nova_animal_count,
                    "report": inc.nova_report,
                    "deterrent_type": inc.nova_deterrent_type,
                    "voice_model": inc.voice_model,
                    "sonic_attempted": inc.sonic_attempted,
                    "has_voice_alert": inc.has_voice_alert,
                    "nova_act_report": inc.nova_act_report,
                    "advisories": inc.advisories
                } if inc.nova_threat_confirmed else None,
                "embedding_dims": inc.embedding_dims,
                "similar_incidents": inc.similar_incidents,
                "alerts_sent": inc.alerts_sent,
                "neighbors_notified": inc.neighbors_notified,
                "pipeline_ms": inc.pipeline_ms
            })
        
        return JSONResponse(result)
    finally:
        db.close()

@app.get("/api/sse")
async def sse_stream():
    """Server-Sent Events stream for real-time pipeline updates"""
    queue = nova_sse.subscribe()
    
    async def event_generator():
        try:
            # Send initial connection success
            yield f"event: connected\ndata: {json.dumps({'step': 'connected', 'message': 'SSE connected'})}\n\n"
            
            while True:
                try:
                    # Wait for message with a timeout for heartbeat
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    parsed = json.loads(data)
                    step = parsed.get('step', 'unknown')
                    
                    # Send with proper event type for frontend
                    if step == 'heartbeat':
                        yield f"event: heartbeat\ndata: {data}\n\n"
                    elif step in ['yolo', 'detection']:
                        yield f"event: detection\ndata: {data}\n\n"
                    elif step in ['nova_lite', 'nova_report', 'nova_analysis']:
                        yield f"event: nova_analysis\ndata: {data}\n\n"
                    else:
                        # Default everything else to pipeline for the log
                        yield f"event: pipeline\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'step': 'heartbeat', 'message': 'keepalive'})}\n\n"
        except Exception as e:
            print(f"SSE error: {e}")
        finally:
            nova_sse.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/test_push")
def test_push(payload: Dict[str, Any] = Body(default={})):
    """
    Test Push Notifications right away.
    """
    msg = (payload.get("message") or "TEST ALERT from FarmGuard").strip()
    ok, info = send_push_notification("Test Alert", msg)
    return {"ok": ok, "message": info}


@app.post("/report_incident")
def report_incident(payload: Dict[str, Any] = Body(...)):
    """
    Endpoint for Modal (or any external service) to report an incident.
    It triggers Nova analysis and SMS in the background.
    """
    phone = payload.get("phone", "").strip()
    label = payload.get("label", "").strip()
    conf = float(payload.get("confidence", 0.0))
    b64 = payload.get("image_b64", "")
    camera_id = payload.get("camera_id", "unknown")
    bbox = payload.get("bbox", None)  # Extract bounding box coordinates [x1, y1, x2, y2]
    
    if not b64:
        return JSONResponse({"ok": False, "error": "Missing image_b64"}, status_code=400)
        
    try:
        img_data = base64.b64decode(b64)
        arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Failed to decode image: {e}"}, status_code=400)
    
    if frame is None:
        return JSONResponse({"ok": False, "error": "Invalid image"}, status_code=400)
        
    print(f"[!] Received incident report from Modal: {label} ({conf:.2f}) from camera {camera_id}")
    print(f"[DEBUG] Payload keys: {list(payload.keys())}")
    print(f"[DEBUG] bbox value: {bbox}")
    print(f"[DEBUG] bbox type: {type(bbox)}")
    
    # Broadcast detection event to SSE
    nova_sse.publish({
        "camera_id": camera_id,
        "step": "yolo",
        "message": f"📡 YOLO Modal detected: {label} ({conf:.0%}) from {camera_id}",
        "data": {
            "animal": label,
            "confidence": conf,
            "bbox": bbox,
            "source": "modal"
        }
    })
    
    # Run NEW pipeline with Nova Sonic + Nova Act in background
    from agents.pipeline import run_detection_pipeline
    threading.Thread(
        target=run_detection_pipeline,
        args=(label, conf, b64, bbox, "modal", camera_id, {}),
        daemon=True
    ).start()
    
    return {"ok": True, "message": "Pipeline started", "camera_id": camera_id}


# -----------------------------
# Telegram Webhook
# -----------------------------

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Handles interactive button clicks from Telegram alerts.
    Callback data format: feedback:incident_id:type (e.g., feedback:19:confirmed)
    """
    try:
        data = await request.json()
        print(f"🤖 Received Telegram webhook: {json.dumps(data)[:200]}...")
        
        callback_query = data.get("callback_query")
        if not callback_query:
            return {"ok": True}
        
        cb_data = callback_query.get("data", "")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        message_id = callback_query.get("message", {}).get("message_id")
        
        if cb_data.startswith("feedback:"):
            _, inc_id_str, feedback_type = cb_data.split(":")
            inc_id = int(inc_id_str)
            
            print(f"✅ User feedback for #{inc_id}: {feedback_type}")
            
            # 1. Update DB & Dataset via pipeline agent
            from agents.pipeline import handle_farmer_feedback
            success = handle_farmer_feedback(inc_id, feedback_type)
            
            # 2. Update the message on Telegram to show visual confirmation
            # Remove buttons and update caption
            original_caption = callback_query.get("message", {}).get("caption", "")
            status_text = "✅ CONFIRMED THREAT" if feedback_type == "confirmed" else "❌ FALSE POSITIVE"
            new_caption = f"{original_caption}\n\n*Result: {status_text}*"
            
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageCaption",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "caption": new_caption,
                    "parse_mode": "Markdown",
                    "reply_markup": {"inline_keyboard": []} # Remove buttons
                }
            )
            
            # 3. Answer callback query to stop loading spinner on Telegram
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": callback_query.get("id"), "text": f"Detections updated: {feedback_type}"}
            )
            
            # 4. Broadcast to SSE so Dashboard updates too
            nova_sse.publish({
                "camera_id": "system",
                "step": "feedback",
                "message": f"Farmer marked Incident #{inc_id} as {feedback_type}",
                "data": {"incident_id": inc_id, "feedback": feedback_type}
            })
            
        return {"ok": True}
    except Exception as e:
        print(f"❌ Error in Telegram webhook: {e}")
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

# -----------------------------
# Stream Management Endpoints
# -----------------------------

# Global state for active streams
active_streams: Dict[str, Any] = {}  # {stream_id: {"modal_url": url}}

def start_modal_inference(stream_id: str, source_url: str) -> Optional[str]:
    """
    Start Modal.com inference for a specific camera stream
    Modal processes the video stream and sends webhooks on detections
    """
    try:
        # Publish initial SSE immediately to provide instant feedback
        nova_sse.publish({
            "camera_id": stream_id,
            "step": "stream_start",
            "message": f"🚀 Initializing inference for {stream_id}...",
            "data": {},
            "timestamp": datetime.utcnow().isoformat()
        })

        # Pre-resolve YouTube URLs locally to bypass Modal's data-center IP block
        if is_youtube(source_url):
            nova_sse.publish({
                "camera_id": stream_id,
                "step": "resolving_youtube",
                "message": "🔗 Resolving YouTube stream URL locally...",
                "data": {},
                "timestamp": datetime.utcnow().isoformat()
            })
            try:
                source_url = resolve_youtube_to_direct_url(source_url)
                print(f"[*] Local YouTube Resolution successful: {(str(source_url) if source_url else '')[:100]}...")
            except Exception as e:
                raise RuntimeError(f"YouTube Resolution Failed: {str(e)}")

        print(f"[*] Starting Modal inference for stream {stream_id}: {str(source_url)[:100]}...")
        
        # Publish SSE that stream is starting on Modal
        nova_sse.publish({
            "camera_id": stream_id,
            "step": "modal_launch",
            "message": f"🎥 Launching Modal YOLO inference engine...",
            "data": {"source_url": (str(source_url) if source_url else "")[:100]},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Build webhook URL using the public tunnel URL so Modal can reach us
        webhook_url = f"{PUBLIC_WEBHOOK_BASE}/report_incident"
        
        # Modal stream endpoint with parameters
        modal_stream_url = (
            f"{MODAL_API_URL}"
            f"?source={requests.utils.quote(source_url)}"
            f"&camera_id={stream_id}"
            f"&webhook_url={requests.utils.quote(webhook_url)}"
        )
        
        print(f"[*] Modal stream URL: {modal_stream_url}")
        
        # Just record the URL — the browser connects directly to Modal for the MJPEG stream
        # Modal sends webhooks to our backend when threats are detected
        active_streams[stream_id] = {
            "modal_url": modal_stream_url
        }
        
        nova_sse.publish({
            "camera_id": stream_id,
            "step": "stream_active",
            "message": f"✅ Modal stream active - YOLO detecting animals in real-time",
            "data": {},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"[+] Modal inference started for {stream_id}")
        return modal_stream_url
        
    except Exception as e:
        print(f"[X] Failed to start Modal inference: {e}")
        return None

def stop_modal_inference(stream_id: str):
    """Stop Modal.com inference for a specific stream"""
    try:
        print(f"[-] Stopping Modal inference for stream {stream_id}")
        
        # Remove from active streams (thread will stop itself)
        if stream_id in active_streams:
            active_streams.pop(stream_id, None)
            print(f"[+] Modal inference stopped for {stream_id}")
            return True
        else:
            print(f"[!] Stream {stream_id} was not active")
            return True
            
    except Exception as e:
        print(f"[X] Failed to stop Modal inference: {e}")
        return False

@app.post("/api/streams/{stream_id}/start")
def start_stream_inference(stream_id: str):
    """Start Modal inference for a specific stream"""
    stream = get_stream_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if not stream.get('url'):
        raise HTTPException(status_code=400, detail="Stream URL is required to start inference")
    
    try:
        modal_url = start_modal_inference(stream_id, stream['url'])
        if modal_url:
            # Update stream status
            update_stream(stream_id, active=True)
            return {"ok": True, "modal_url": modal_url, "message": f"Inference started for {stream['name']}", "stream_id": stream_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to start Modal inference")
    except RuntimeError as re:
        print(f"[X] Startup error: {re}")
        raise HTTPException(status_code=400, detail=str(re))
    except Exception as e:
        print(f"[X] Unexpected startup error: {e}")
        raise HTTPException(status_code=500, detail=f"Inference startup failed: {str(e)}")

@app.post("/api/streams/{stream_id}/stop")
def stop_stream_inference(stream_id: str):
    """Stop Modal inference for a specific stream"""
    stream = get_stream_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    success = stop_modal_inference(stream_id)
    
    if success:
        # Update stream status
        update_stream(stream_id, active=False)
        return {"ok": True, "message": f"Inference stopped for {stream['name']}", "stream_id": stream_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to stop Modal inference")

@app.get("/api/streams")
def get_streams():
    """Get all camera streams with live active status"""
    streams = load_streams()
    for s in streams:
        sid = s.get('id')
        if sid in active_streams:
            s['active'] = True
            s['modal_url'] = active_streams[sid].get('modal_url')
        else:
            s['active'] = False
            s['modal_url'] = None
    return streams

@app.post("/api/streams")
def create_stream(payload: Dict[str, Any] = Body(...)):
    """Create a new camera stream"""
    name = payload.get("name", "").strip()
    url = payload.get("url", "").strip()
    stream_type = payload.get("type", "RTSP").strip()
    auto_start = payload.get("auto_start", False)
    
    if not name:
        raise HTTPException(status_code=400, detail="Stream name is required")
    
    new_stream = add_stream(name, url, stream_type)
    
    # Optionally start Modal inference for this stream
    if auto_start and url:
        try:
            # Trigger Modal inference in background
            threading.Thread(
                target=start_modal_inference,
                args=(new_stream['id'], url),
                daemon=True
            ).start()
            new_stream['inference_started'] = True
        except Exception as e:
            print(f"Failed to start Modal inference: {e}")
            new_stream['inference_started'] = False
    
    return {"ok": True, "stream": new_stream}

@app.put("/api/streams/{stream_id}")
def edit_stream(stream_id: str, payload: Dict[str, Any] = Body(...)):
    """Update an existing stream"""
    name = payload.get("name")
    url = payload.get("url")
    stream_type = payload.get("type")
    active = payload.get("active")
    
    updated = update_stream(stream_id, name, url, stream_type, active)
    if not updated:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return {"ok": True, "stream": updated}

@app.delete("/api/streams/{stream_id}")
def remove_stream(stream_id: str):
    """Delete a stream"""
    success = delete_stream(stream_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    return {"ok": True, "message": "Stream deleted"}


# -----------------------------
# Telegram Voice Integration
# -----------------------------

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Handles ALL Telegram interactions:
    
    1. /start <topic>     → Link farmer's chat to their farm
    2. Callback query      → YES/NO feedback on threat alerts
    3. Voice message       → Farmer asks status, Nova Sonic responds
    4. Text "status"       → Text-based status check
    """
    from config import TELEGRAM_BOT_TOKEN
    from agents.pipeline import handle_farmer_feedback
    import asyncio
    
    # Set token in nova_sonic_agent
    from agents import nova_sonic_agent
    nova_sonic_agent.set_telegram_token(TELEGRAM_BOT_TOKEN)
    
    body = await request.json()
    
    # ── Case 1: Callback query (YES/NO buttons on alerts) ──
    if "callback_query" in body:
        cb = body["callback_query"]
        data = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]
        cb_id = cb["id"]
        
        # Parse feedback:incident_id:action format
        if data.startswith("feedback:"):
            parts = data.split(":")
            if len(parts) == 3:
                _, incident_id, action = parts
                incident_id = int(incident_id)
                
                success = handle_farmer_feedback(incident_id, action)
                
                # Answer the callback (removes loading spinner)
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                        json={
                            "callback_query_id": cb_id,
                            "text": "✅ Confirmed as real threat" if action == "confirmed" 
                                    else "❌ Marked as false positive"
                        }
                    )
                    
                    # Edit the original message to show feedback was recorded
                    await client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageCaption",
                        json={
                            "chat_id": chat_id,
                            "message_id": cb["message"]["message_id"],
                            "caption": cb["message"].get("caption", "") + 
                                       f"\n\n{'✅ CONFIRMED' if action == 'confirmed' else '❌ FALSE POSITIVE'} by farmer"
                        }
                    )
        
        return {"ok": True}
    
    # ── Case 2: Regular message ──
    message = body.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    
    if not chat_id:
        return {"ok": True}
    
    # ── Case 2a: Voice message → Nova Sonic ──
    if "voice" in message:
        voice = message["voice"]
        file_id = voice["file_id"]
        duration = voice.get("duration", 0)
        
        print(f"[TELEGRAM] Voice message from {chat_id}, {duration}s")
        
        # Process in background to respond quickly
        asyncio.create_task(
            _handle_voice_message(chat_id, file_id, duration)
        )
        
        return {"ok": True}
    
    # ── Case 2b: /start command → Link farm ──
    text = message.get("text", "").strip()
    
    if text.startswith("/start"):
        parts = text.split()
        topic = parts[1] if len(parts) > 1 else None
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "🐾 *PAWS Activated*\n\n"
                        "Your farm is now linked. You'll receive:\n"
                        "• 📸 Photo alerts with threat details\n"
                        "• ✅/❌ Buttons to confirm or reject\n"
                        "• 🎤 Send a voice message anytime to ask about farm status\n\n"
                        f"{'Linked to topic: ' + topic if topic else 'Send /start <your-ntfy-topic> to link'}"
                    ),
                    "parse_mode": "Markdown"
                }
            )
        
        return {"ok": True}
    
    # ── Case 2c: Text "status" → Quick status response ──
    if text.lower() in ["status", "update", "report", "check"]:
        asyncio.create_task(_handle_status_query(chat_id))
        return {"ok": True}
    
    # ── Case 2d: Any other text ──
    if text:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        "🐾 PAWS Commands:\n"
                        "• 🎤 Send a *voice message* → Get spoken farm status\n"
                        "• Type *status* → Get text status update\n"
                        "• /start <topic> → Link your farm"
                    ),
                    "parse_mode": "Markdown"
                }
            )
    
    return {"ok": True}


async def _handle_voice_message(chat_id: int, file_id: str, duration: int):
    """
    Full voice processing pipeline:
    Telegram voice → Download → Nova Sonic → Voice reply
    """
    from agents.nova_sonic_agent import (
        download_telegram_voice,
        process_voice_with_sonic,
        send_telegram_voice
    )
    from config import TELEGRAM_BOT_TOKEN
    
    try:
        # Send "recording voice" action so farmer sees typing indicator
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendChatAction",
                json={"chat_id": chat_id, "action": "record_voice"}
            )
        
        # Step 1: Download voice from Telegram
        print(f"[VOICE] Downloading {duration}s voice from Telegram...")
        audio_bytes = await download_telegram_voice(file_id)
        print(f"[VOICE] Downloaded {len(audio_bytes)} bytes")
        
        # Step 2: Build farm context from DB
        db = SessionLocal()
        try:
            from models.incident import Incident
            recent = db.query(Incident).order_by(
                Incident.created_at.desc()
            ).limit(5).all()
            
            farm_context = {
                "region": recent[0].region if recent else "default",
                "language": "en",
                "active_threats": len([
                    i for i in recent 
                    if i.status == "alerted" 
                    and i.created_at 
                    and (datetime.utcnow() - i.created_at).total_seconds() < 3600
                ]),
                "recent_incidents": [{
                    "animal": i.animal,
                    "severity": i.nova_severity or 0,
                    "behavior": i.nova_behavior or "unknown",
                    "minutes_ago": int(
                        (datetime.utcnow() - i.created_at).total_seconds() / 60
                    ) if i.created_at else 999
                } for i in recent]
            }
        finally:
            db.close()
        
        # Step 3: Process with Nova Sonic (or fallback)
        print(f"[VOICE] Processing with Nova Sonic...")
        result = await process_voice_with_sonic(audio_bytes, farm_context)
        print(f"[VOICE] Model used: {result.get('model')}, success: {result.get('success')}")
        
        # Step 4: Send voice response back
        caption = f"🤖 PAWS AI ({result.get('model', 'unknown')})"
        if result.get("transcript_out"):
            caption += f"\n\n📝 {result['transcript_out'][:500]}"
        
        if result.get("success") and result.get("audio_b64"):
            await send_telegram_voice(
                chat_id, result["audio_b64"], caption,
                audio_format=result.get("audio_format", "ogg"),
            )
        else:
            # Send text if voice generation failed
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": (
                            f"🐾 PAWS Status:\n\n"
                            f"{result.get('transcript_out', 'Unable to process voice. Type status for text update.')}"
                        )
                    }
                )
        
        # Log to SSE for dashboard visibility
        nova_sse.publish({
            "step": "sonic",
            "message": f"Voice query from farmer (chat {chat_id}) → "
                       f"Responded via {result.get('model', 'unknown')}",
            "data": {
                "chat_id": chat_id,
                "model": result.get("model"),
                "transcript_out": result.get("transcript_out", "")[:200],
                "sonic_attempted": result.get("sonic_attempted", True)
            }
        })
        
    except Exception as e:
        print(f"[VOICE ERROR] {e}")
        import traceback
        traceback.print_exc()
        
        from config import TELEGRAM_BOT_TOKEN
        
        # Send error message to farmer
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "⚠️ Voice processing temporarily unavailable. Type *status* for a text update.",
                    "parse_mode": "Markdown"
                }
            )


async def _handle_status_query(chat_id: int):
    """Text-based status when farmer types 'status'."""
    from config import TELEGRAM_BOT_TOKEN
    
    db = SessionLocal()
    try:
        from models.incident import Incident
        recent = db.query(Incident).order_by(
            Incident.created_at.desc()
        ).limit(5).all()
        
        if not recent:
            text = "🐾 *PAWS Status*\n\n✅ All clear. No incidents detected.\nMonitoring is active."
        else:
            active = [i for i in recent if i.status == "alerted"]
            text = f"🐾 *PAWS Status*\n\n"
            text += f"📊 Last 5 incidents:\n"
            for i in recent:
                age = ""
                if i.created_at:
                    mins = int((datetime.utcnow() - i.created_at).total_seconds() / 60)
                    age = f"{mins}m ago" if mins < 60 else f"{mins//60}h ago"
                
                icon = "🔴" if (i.nova_severity or 0) >= 7 else "🟡" if (i.nova_severity or 0) >= 4 else "🟢"
                text += (
                    f"{icon} {i.animal} — severity {i.nova_severity or '?'}/10 "
                    f"({i.nova_behavior or '?'}) {age}\n"
                )
            
            if active:
                text += f"\n⚠️ {len(active)} active threat(s)"
            else:
                text += f"\n✅ No active threats"
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
            )
    finally:
        db.close()


@app.get("/api/advisories/{region}")
async def get_advisories(region: str):
    """Get wildlife advisories for a region via Nova Act."""
    from agents.nova_act_agent import get_regional_advisories
    result = await get_regional_advisories(region)
    return result


@app.get("/api/emergency-contacts/{region}")
async def get_contacts(region: str):
    """Get emergency wildlife contacts via Nova Act."""
    from agents.nova_act_agent import get_emergency_contacts
    result = await get_emergency_contacts(region)
    return result


@app.post("/api/voice-query")
async def voice_query(request: Request):
    """Farmer sends voice, gets spoken response via Nova Sonic."""
    from agents.nova_sonic_agent import process_farmer_voice
    body = await request.json()
    audio_b64 = body.get("audio_b64", "")
    farm_context = body.get("farm_context", {})
    
    # Add recent incidents to context
    db = SessionLocal()
    try:
        from models.incident import Incident
        recent = db.query(Incident).order_by(
            Incident.created_at.desc()
        ).limit(5).all()
        farm_context["recent_incidents"] = [{
            "animal": i.animal,
            "severity": i.nova_severity,
            "minutes_ago": int((datetime.utcnow() - i.created_at).total_seconds() / 60) if i.created_at else 0
        } for i in recent]
        farm_context["active_threats"] = len([i for i in recent if i.status == "alerted"])
    finally:
        db.close()
    
    from agents.nova_sonic_agent import process_voice_with_sonic
    result = await process_voice_with_sonic(base64.b64decode(audio_b64), farm_context)
    return result


# -----------------------------
# Server Startup
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    print("\n🚀 Starting PAWS Backend Server...")
    print(f"📡 API will be available at: http://localhost:{port}")
    print(f"📚 API docs at: http://localhost:{port}/docs")
    print(f"🔔 Push notifications: ntfy.sh/{NTFY_TOPIC}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
