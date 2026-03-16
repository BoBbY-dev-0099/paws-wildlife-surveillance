# PAWS — Perimeter AI Wildlife Surveillance

Real-time wildlife intrusion detection system that protects farmland using computer vision and Amazon Nova foundation models. PAWS connects any IP camera to a GPU-accelerated inference pipeline, classifies threats via multi-modal AI analysis, and dispatches multi-channel alerts — all within seconds.

Built for the **Amazon Nova Hackathon 2026**.

## How It Works

```
Camera (HLS/RTSP) ──► Modal.com T4 GPU ──► YOLO-World Detection ──► Amazon Nova Lite Analysis
                          │                        │                          │
                     Bounding Boxes            Webhook to Backend         Severity Score
                     drawn on stream           with frame sequence        + Behavior Report
                                                      │
                                    ┌─────────────────┼──────────────────┐
                                    ▼                  ▼                  ▼
                              ntfy.sh Push      Telegram Bot       Community Mesh
                              Notification      (with photos       (15km radius
                                                + feedback)        farm-to-farm)
```

**Pipeline steps:** Gate → Debounce → DB Write → Nova Lite Vision → Nova Embed → Similarity Search → Threat Decision → Report Generation → Polly Voice Alert → Alert Dispatch → Mesh Broadcast → Deterrent Trigger → Dataset Archive → Complete

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | SvelteKit, Tailwind CSS, SSE, lucide-svelte |
| **Backend** | FastAPI, SQLAlchemy (SQLite), python-dotenv |
| **Inference** | Modal.com (T4 GPU), YOLO-World v2, OpenCV |
| **AI Analysis** | Amazon Nova Lite (vision), Nova Embed (similarity), Amazon Polly (TTS) |
| **Alerts** | ntfy.sh, Telegram Bot API, Amazon SNS (SMS) |
| **Streaming** | HLS, RTSP, MJPEG, yt-dlp (YouTube resolution) |

## Amazon Nova Models Used

- **Amazon Nova 2 Lite** — Multi-frame vision analysis: identifies animal species, behavior (charging/stalking/grazing), proximity to perimeter, and generates severity scores (1–10)
- **Amazon Nova Multimodal Embedding** — Encodes detection frames into vectors for similarity search against historical incidents
- **Amazon Polly** — Converts threat reports into spoken alerts in 6 languages (EN, HI, SW, ES, PT, AR)

## Project Structure

```
├── config.py                       # Environment config, region-animal mapping
├── sse.py                          # Server-Sent Events manager
├── requirements.txt                # Python dependencies
├── .env.example                    # Template (no secrets)
│
├── agents/
│   ├── pipeline.py                 # 14-step detection pipeline orchestrator
│   ├── nova_agent.py               # Nova Lite + Polly API calls
│   ├── alert_agent.py              # ntfy, Telegram, mesh dispatch
│   ├── dataset_agent.py            # Auto-archive detections for retraining
│   ├── deterrent_agent.py          # Edge device trigger (ultrasonic/strobe)
│   ├── nova_sonic_agent.py         # Nova Sonic speech-to-speech (experimental)
│   └── nova_act_agent.py           # Nova Act browser automation (experimental)
│
├── backend_fastapi/
│   ├── main.py                     # FastAPI server — all API routes, stream mgmt
│   ├── modal_inference.py          # Modal.com GPU container (YOLO-World)
│   ├── stream_manager.py           # Camera CRUD (persisted to streams.json)
│   ├── nova_agent.py               # Nova analysis wrapper
│   ├── yt_resolver.py              # YouTube → direct URL resolver
│   └── sse.py                      # SSE event bus
│
└── paws-dashboard/                 # SvelteKit frontend
    └── src/
        ├── routes/
        │   ├── +page.svelte        # Landing page
        │   └── dashboard/
        │       └── +page.svelte    # Main dashboard
        └── lib/components/
            ├── LiveFeedPage.svelte  # Camera feed + inference controls
            ├── IncidentsPage.svelte # Incident history
            ├── DashboardLayout.svelte # Navigation + theming
            ├── MeshPage.svelte     # Community mesh network
            ├── DatasetPage.svelte  # Training data browser
            ├── AgentsPage.svelte   # Agent status monitor
            └── SettingsPage.svelte # Configuration
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- AWS account with Bedrock access (Nova Lite, Nova Embed, Polly)
- Modal.com account (free tier works)

### Install & Run

```bash
# Backend
cp .env.example .env          # Fill in your AWS keys, Telegram token
pip install -r requirements.txt
cd backend_fastapi
python main.py                # Starts on :8000

# Frontend (separate terminal)
cd paws-dashboard
npm install
npm run dev                   # Starts on :5173

# Deploy Modal inference (one-time)
modal deploy backend_fastapi/modal_inference.py
```

### Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Yes | IAM key with Bedrock + Polly access |
| `AWS_SECRET_ACCESS_KEY` | Yes | IAM secret |
| `TELEGRAM_BOT_TOKEN` | No | From @BotFather for Telegram alerts |
| `TELEGRAM_CHAT_IDS` | No | Comma-separated recipient IDs |
| `NTFY_TOPIC` | No | Custom ntfy.sh topic for push alerts |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sse` | Real-time pipeline events (SSE) |
| `GET` | `/api/incidents` | List all incidents |
| `GET` | `/api/streams` | List camera streams |
| `POST` | `/api/streams` | Add a camera stream |
| `DELETE` | `/api/streams/{id}` | Remove a stream |
| `POST` | `/api/streams/{id}/start` | Start GPU inference |
| `POST` | `/api/streams/{id}/stop` | Stop GPU inference |
| `POST` | `/api/simulate/{scenario}` | Trigger test detection |
| `POST` | `/api/detect` | Webhook for YOLO detections |
| `POST` | `/api/feedback/{id}` | Human verification |
| `POST` | `/report_incident` | Modal webhook callback |

## Testing

Add a stream in the dashboard using this public elephant camera:

```
https://elephants.hls.camzonecdn.com/CamzoneStreams/elephants/Playlist.m3u8
```

Click **Start Inference** — Modal spins up a T4 GPU container, runs YOLO-World detection, draws bounding boxes on the live feed, and sends webhook callbacks to the backend when elephants are detected. The full 14-step Nova pipeline executes automatically.

## License

MIT
