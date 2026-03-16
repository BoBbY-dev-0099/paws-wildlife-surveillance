## Inspiration

Human-wildlife conflict kills over 100 people and thousands of livestock annually across South Asia and Sub-Saharan Africa. Farmers in Nepal, Kenya, and India lose entire harvests overnight to a single elephant herd crossing their perimeter. The existing solutions — electric fences, watchtowers, manual patrols — are either too expensive, too slow, or too dangerous. A farmer asleep at 2am has no warning when a tiger approaches the cattle pen.

We asked: what if any cheap IP camera could become an intelligent perimeter guard that detects, analyzes, and alerts within seconds — and gets smarter with every encounter?

## What it does

PAWS turns any camera feed (HLS, RTSP, IP cam, or even a YouTube live stream) into a real-time wildlife threat detection system. When a dangerous animal enters the frame:

1. **YOLO-World** running on a cloud GPU identifies the species and draws bounding boxes on the live stream
2. **Amazon Nova Lite** receives a sequence of 5 frames and performs multi-modal threat analysis — classifying behavior (charging, stalking, grazing, at fence), estimating distance, scoring severity 1–10, and recommending a specific deterrent
3. **Amazon Nova Embed** encodes the detection into a vector and searches past incidents for similar patterns, reducing false positives
4. **Amazon Polly** generates a spoken voice alert in the farmer's language (supports English, Hindi, Swahili, Spanish, Portuguese, Arabic)
5. Alerts fire simultaneously across **ntfy.sh** (push notification), **Telegram** (with detection photos and one-tap feedback buttons), and a **community mesh network** that warns neighboring farms within 15km

The SvelteKit dashboard shows the annotated live feed, a real-time pipeline trace of all 14 steps, Nova's analysis panel, and incident history. Farmers can mark detections as confirmed or false positive directly from Telegram, and those labels feed back into the training dataset automatically.

## How we built it

**Backend:** FastAPI serves the API, manages camera streams, and orchestrates a 14-step detection pipeline. Each step publishes Server-Sent Events so the dashboard updates in real-time. The pipeline runs in background threads to never block the API.

**GPU Inference:** We deployed YOLO-World v2 on Modal.com's serverless T4 GPUs. The Modal container opens the camera stream via OpenCV, runs inference at ~10 FPS, draws bounding boxes with color-coded threat levels (green → cyan → red), and yields annotated frames as an MJPEG stream. When a threat exceeds the alert threshold, it sends a webhook with a 5-frame sequence to the backend.

**AI Analysis:** Amazon Nova Lite receives the frame sequence with farm context (GPS region, language, known species) and returns structured JSON — species, behavior classification, severity score, deterrent recommendation, and alert translations in 6 languages. Nova Embed converts the detection into a vector for similarity search against historical incidents stored in the database.

**Alerts:** The dispatch layer fires ntfy.sh push notifications, Telegram messages with inline photos and feedback buttons, Amazon Polly voice alerts, and mesh broadcasts to neighboring farms via region-scoped ntfy channels.

**Frontend:** SvelteKit with Tailwind CSS. Three themes (dark, light, green). The Live Feed page lets you add/remove camera streams, start/stop GPU inference per camera, and watch the annotated MJPEG feed. The pipeline terminal shows every step with timestamps and latency.

**Region awareness:** GPS coordinates map to a geographic region (Africa, Asia, Americas, Europe, Oceania, MENA), and each region has its own dangerous animal vocabulary. A farm in Kenya detects elephants and hyenas; a farm in Montana detects bears and wolves.

## Challenges we ran into

**YouTube IP blocking on Modal:** We initially supported YouTube live streams as camera sources. yt-dlp resolved the stream URL locally, but Google's CDN segments are IP-locked — Modal's datacenter IPs got 403'd. We solved it by resolving URLs on the local backend before passing the direct stream URL to Modal, though some streams still timeout due to geographic restrictions.

**MJPEG rendering in browsers:** Modal's inference endpoint outputs `multipart/x-mixed-replace` MJPEG frames. Chrome and Edge handle this inconsistently with `<img>` tags. We went through three iterations — direct `<img>` to Modal, a backend proxy parsing MJPEG frames, and snapshot polling via canvas — before settling on the approach that balanced latency and reliability.

**Unicode encoding on Windows:** Modal CLI deployment crashed with `charmap codec can't encode character` errors on Windows PowerShell because the Python print statements contained emoji. We had to replace all unicode characters in the Modal container code with ASCII equivalents.

**Cold start latency:** Modal's serverless GPU containers take 15–30 seconds on cold start. The first inference request after idle triggers model download and CUDA initialization. We mitigated this with a 120-second scaledown window so the container stays warm between requests.

## Accomplishments that we're proud of

- **End-to-end working system:** From a raw HLS camera URL to a Telegram alert with detection photo, severity score, and one-tap feedback — all automated, under 5 seconds on warm containers
- **Real detections on real cameras:** We tested against live elephant cameras in Africa and successfully detected elephants, hippos, and bears with bounding boxes and Nova analysis
- **14-step pipeline with full observability:** Every step from gate-check to dataset-archive publishes SSE events. You can watch the entire pipeline execute in the dashboard terminal in real-time
- **Farmer feedback loop:** Telegram inline buttons let farmers confirm or reject detections. Those labels automatically sort into `confirmed_threat`, `false_positive`, and `nova_rejected` dataset folders — building a training set for future fine-tuning
- **Multi-language voice alerts:** Amazon Polly generates spoken warnings in the farmer's local language, critical for regions with low literacy

## What we learned

- Amazon Nova Lite is genuinely capable at structured visual reasoning — it reliably distinguishes an elephant grazing from an elephant charging at a fence, and its severity scores correlate well with actual threat level
- Nova Embed provides useful similarity vectors for incident deduplication, reducing repeated alerts for the same animal lingering near the perimeter
- Serverless GPU inference (Modal) is powerful but cold starts are a real UX problem for real-time systems — pre-warming strategies are essential
- Building for farmers means building for unreliable connectivity, low-end devices, and non-English languages. Push notifications via ntfy.sh work even on basic smartphones without installing an app

## What's next for PAWS — Perimeter AI Wildlife Surveillance

- **Edge inference:** Port YOLO-World to NVIDIA Jetson or Raspberry Pi 5 for local inference with zero cloud latency, using the labeled dataset we've been collecting
- **Amazon Nova Sonic integration:** Replace text-to-speech with Nova Sonic's speech-to-speech for natural conversational voice alerts and two-way farmer communication
- **Amazon Nova Act automation:** Auto-file wildlife incident reports with local conservation authorities and pull regional wildlife advisory data
- **Fine-tuned detection model:** Train a custom YOLOv8 model on the confirmed threat images collected through farmer feedback, improving accuracy for region-specific species
- **SMS fallback via Amazon SNS:** For areas without internet, fall back to SMS alerts with severity score and recommended action
- **Mesh network scaling:** Expand the community mesh from ntfy-based pub/sub to a proper P2P protocol that works offline between nearby farms via Bluetooth or LoRa
