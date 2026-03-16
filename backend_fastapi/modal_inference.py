import modal

# ----------------------------------------------------
# 1. Image Definition
# ----------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1-mesa-glx", "libglib2.0-0", "git", "ffmpeg")
    .pip_install(
        "ultralytics>=8.1",
        "opencv-python-headless",
        "numpy",
        "fastapi",
        "yt-dlp",
        "requests",
        "transformers",
    )
    .run_commands("pip install git+https://github.com/openai/CLIP.git")
    .add_local_file("../../config.py", remote_path="/root/config.py")
)

# ----------------------------------------------------
# 2. Volume for Model Weights
# ----------------------------------------------------
vol = modal.Volume.from_name("paws-weights-volume", create_if_missing=True)

# ----------------------------------------------------
# 3. Modal App Definition
# ----------------------------------------------------
app = modal.App("paws-vision-engine", image=image)

# Weights mount point
MODEL_DIR = "/weights"
MODEL_PATH = f"{MODEL_DIR}/best.pt"

# Global state for cross-instance coordination
global_state = modal.Dict.from_name("paws-engine-state", create_if_missing=True)

# ----------------------------------------------------
# 4. Helpers
# ----------------------------------------------------
def is_probably_youtube(url: str) -> bool:
    u = (url or "").lower()
    return ("youtube.com" in u) or ("youtu.be" in u) or ("m.youtube.com" in u)

def resolve_youtube_to_direct_url(url: str) -> str:
    import yt_dlp
    ydl_opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True, "format": "best",
        "extractor_args": {"youtube": {"player_client": ["android", "ios"]}},
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return info.get("url")
        except Exception as e:
            raise RuntimeError(f"YouTube resolution failed: {e}")

# ----------------------------------------------------
# 5. Vision Engine Class
# ----------------------------------------------------
@app.cls(
    gpu="T4",
    volumes={MODEL_DIR: vol},
    scaledown_window=120,
    max_containers=1,
)
class VideoInferenceEngine:
    def __init__(self):
        self.world_model = None
        self.custom_model = None
        self.active_classes = []

    @modal.enter()
    def load_model(self):
        import os
        from ultralytics import YOLO, YOLOWorld
        from config import REGION_ANIMAL_CLASSES
        
        print("[*] PAWS Container initializing... Loading Vision Models")
        
        # Merge key classes for broad detection
        threat_classes = ["elephant", "tiger", "bear", "lion", "leopard", "hyena", "baboon", "wolf", "jaguar", "wild boar", "crocodile", "hippopotamus", "puma", "coyote", "wild dog"]
        common_classes = ["cow", "human", "dog", "deer", "monkey"]
        self.active_classes = sorted(list(set(threat_classes + common_classes)))
        
        print(f"[+] Detection Vocabulary ({len(self.active_classes)}): {self.active_classes}")
        
        self.world_model = YOLOWorld("yolov8s-worldv2.pt")
        self.world_model.set_classes(self.active_classes)
        self.world_model.to('cuda')
        
        # Optional custom weights (not used for boxes right now to keep it clean)
        if os.path.exists(MODEL_PATH):
            self.custom_model = YOLO(MODEL_PATH)
            self.custom_model.to('cuda')
            print("[+] Custom weights loaded.")

    def _infer(self, source: str, camera_id: str = "", phone: str = "", webhook_url: str = "", webhook_secret: str = ""):
        import cv2
        import time
        import requests
        import base64
        import threading
        from collections import deque

        # THREAT LIST (Only these trigger alerts/state updates)
        THREATS = set(["elephant", "tiger", "bear", "lion", "leopard", "hyena", "baboon", "wolf", "jaguar", "wild boar", "crocodile", "hippopotamus", "puma", "coyote", "wild dog"])
        
        # THRESHOLDS
        VISUAL_CONF = 0.20   # Very sensitive for boxes
        ALERT_CONF = 0.40    # Threshold for Nova/Alerts
        
        COOLDOWN = 180 
        last_alert = {}

        def can_alert(label):
            now = time.time()
            if label not in last_alert or (now - last_alert[label]) > COOLDOWN:
                last_alert[label] = now
                return True
            return False

        def send_webhook(label, conf, images_b64):
            """Send detection to webhook endpoint"""
            if not webhook_url:
                return
            
            try:
                payload = {
                    "camera_id": camera_id,
                    "phone": phone,
                    "label": label,
                    "confidence": float(conf),
                    "image_b64": images_b64[0] if images_b64 else "",
                    "images_b64": images_b64,
                    "timestamp": time.time()
                }
                
                if webhook_secret:
                    payload["secret"] = webhook_secret
                
                response = requests.post(webhook_url, json=payload, timeout=5)
                if response.status_code == 200:
                    print(f"[+] Webhook sent: {label} to {webhook_url}")
                else:
                    print(f"[!] Webhook failed: {response.status_code}")
            except Exception as e:
                print(f"[X] Webhook error: {e}")

        src = source
        if is_probably_youtube(src):
            src = resolve_youtube_to_direct_url(src)
        
        print(f"[*] Starting inference for camera: {camera_id or 'unknown'}")
        print(f"[*] Source: {src[:100]}...")
        
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print(f"[X] Failed to open stream: {src}")
            yield b"--frame\r\nContent-Type: text/plain\r\n\r\nError: Stream offline.\r\n"
            return
        
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame_buffer = deque(maxlen=30)
        frame_count = 0
        
        try:
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.01)
                    continue

                frame_count += 1
                
                # In-memory annotated frame
                annotated = frame.copy()

                # Inference
                results = self.world_model.predict(
                    source=frame, imgsz=640, conf=VISUAL_CONF, verbose=False, device='cuda'
                )[0]

                if results.boxes is not None and len(results.boxes) > 0:
                    for box in results.boxes:
                        c_id = int(box.cls[0])
                        label = self.active_classes[c_id]
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].cpu().numpy().astype(int)
                        
                        # 1. VISUAL FEEDBACK (Bounding Box)
                        color = (0, 255, 0) # Default Green
                        if label in THREATS:
                            color = (0, 255, 255) # Cyan for threat detected
                            if conf >= ALERT_CONF:
                                color = (0, 0, 255) # Bright Red for active alert

                        cv2.rectangle(annotated, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 3)
                        # Black background for text for visibility
                        cv2.putText(annotated, f"{label.upper()} {conf:.2f}", (xyxy[0], xyxy[1]-10), 
                                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0,0,0), 4) # Outline
                        cv2.putText(annotated, f"{label.upper()} {conf:.2f}", (xyxy[0], xyxy[1]-10), 
                                    cv2.FONT_HERSHEY_DUPLEX, 0.7, color, 1)

                        # 2. SEVERITY PROCESSING (Background)
                        if label in THREATS and conf >= ALERT_CONF:
                            latest_info = {
                                "camera_id": camera_id,
                                "label": label,
                                "conf": conf,
                                "ts": time.time(),
                                "bbox": xyxy.tolist(),
                                "frame_count": frame_count
                            }
                            
                            if can_alert(label):
                                print(f"[!] THREAT DETECTED [{camera_id}]: {label} ({conf:.2f})")
                                snapshot_buffer = list(frame_buffer)
                                indices = [-1, -7, -14, -21, -28]
                                sequence_b64 = []
                                
                                for idx in indices:
                                    try:
                                        f_to_enc = snapshot_buffer[idx] if len(snapshot_buffer) > abs(idx) else snapshot_buffer[0]
                                        _, enc = cv2.imencode('.jpg', f_to_enc, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                                        sequence_b64.append(base64.b64encode(enc).decode('utf-8'))
                                    except: continue
                                
                                if not sequence_b64:
                                    _, enc = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                                    sequence_b64 = [base64.b64encode(enc).decode('utf-8')]

                                latest_info["images_b64"] = sequence_b64
                                
                                # Update global state
                                if camera_id:
                                    global_state[f"latest_{camera_id}"] = latest_info
                                global_state["latest"] = latest_info
                                
                                # Send webhook in background
                                threading.Thread(
                                    target=send_webhook,
                                    args=(label, conf, sequence_b64),
                                    daemon=True
                                ).start()

                # Yield for direct MJPEG stream
                succ, jpg = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if succ:
                    yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")

                frame_buffer.append(frame.copy())

        finally: 
            cap.release()
            frame_buffer.clear()
            print(f"[-] Inference stopped for camera: {camera_id or 'unknown'}")

    @modal.fastapi_endpoint(method="GET", label="paws-stream")
    def stream_video(self, source: str, camera_id: str = "", phone: str = "", webhook_url: str = "", webhook_secret: str = ""):
        from fastapi.responses import StreamingResponse
        
        print(f"[*] Stream request received:")
        print(f"   Camera ID: {camera_id}")
        print(f"   Source: {source[:100]}...")
        print(f"   Webhook: {webhook_url}")
        
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Camera-ID": camera_id,
        }
        
        return StreamingResponse(
            self._infer(source, camera_id, phone, webhook_url, webhook_secret), 
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=headers
        )


@app.function()
@modal.fastapi_endpoint()
def get_latest(camera_id: str = ""):
    """Bridges detections to local server via polling"""
    if camera_id:
        # Get latest detection for specific camera
        key = f"latest_{camera_id}"
        return global_state.get(key, {"label": None, "ts": 0, "camera_id": camera_id})
    else:
        # Get latest detection from any camera
        return global_state.get("latest", {"label": None, "ts": 0})
