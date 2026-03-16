import os
from dotenv import load_dotenv
load_dotenv()

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
NOVA_MODEL_ID = os.getenv("NOVA_MODEL_ID", "us.amazon.nova-lite-v1:0")

# Nova Embeddings — correct model ID per AWS docs (Dec 2025+)
NOVA_EMBED_MODEL_ID = os.getenv(
    "NOVA_EMBED_MODEL_ID", "amazon.nova-2-multimodal-embeddings-v1:0"
)
NOVA_EMBED_FALLBACK_IDS = [
    "amazon.nova-2-multimodal-embeddings-v1:0",
]

# Nova Sonic — requires aws_sdk_bedrock_runtime (Python 3.12+)
# boto3 does NOT support InvokeModelWithBidirectionalStream
NOVA_SONIC_MODEL_ID = os.getenv(
    "NOVA_SONIC_MODEL_ID", "amazon.nova-sonic-v1:0"
)

FARM_LAT = float(os.getenv("FARM_LAT", "0"))
FARM_LON = float(os.getenv("FARM_LON", "0"))
FARM_LANGUAGE = os.getenv("FARM_LANGUAGE", "en")

NTFY_BASE_URL = os.getenv("NTFY_BASE_URL", "https://ntfy.sh")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "paws-farm-demo")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
MODAL_WEBHOOK_SECRET = os.getenv("MODAL_WEBHOOK_SECRET", "")
MODAL_STREAM_URL = os.getenv("MODAL_STREAM_URL", "")
EDGE_DEVICE_URL = os.getenv("EDGE_DEVICE_URL", "")

ALERT_SEVERITY_THRESHOLD = int(os.getenv("ALERT_SEVERITY_THRESHOLD", "4"))
DETERRENT_SEVERITY_THRESHOLD = int(os.getenv("DETERRENT_SEVERITY_THRESHOLD", "6"))
AUTHORITY_SEVERITY_THRESHOLD = int(os.getenv("AUTHORITY_SEVERITY_THRESHOLD", "8"))
DETECTION_COOLDOWN_SECONDS = int(os.getenv("DETECTION_COOLDOWN_SECONDS", "30"))
DATASET_DIR = os.getenv("DATASET_DIR", "dataset")
DETECTIONS_DIR = os.getenv("DETECTIONS_DIR", "detections")


def gps_to_region(lat: float, lon: float) -> str:
    if lat == 0 and lon == 0: return "default"
    if -35 < lat < 37 and -20 < lon < 55: return "africa"
    if 5 < lat < 55 and 60 < lon < 150: return "asia"
    if -55 < lat < 70 and -170 < lon < -30: return "americas"
    if 35 < lat < 72 and -25 < lon < 45: return "europe"
    if -50 < lat < 0 and 110 < lon < 180: return "oceania"
    if 15 < lat < 42 and 25 < lon < 65: return "mena"
    return "default"

REGION_ANIMAL_CLASSES = {
    "africa":   ["elephant","lion","leopard","hyena","hippo","buffalo","crocodile","baboon","wild_dog"],
    "asia":     ["elephant","tiger","leopard","bear","wild_boar","wolf","snake","monkey","crocodile"],
    "americas": ["bear","wolf","cougar","jaguar","coyote","alligator","wild_boar","moose"],
    "europe":   ["wolf","bear","wild_boar","lynx","fox"],
    "oceania":  ["crocodile","dingo","wild_boar","cassowary"],
    "mena":     ["wolf","hyena","leopard","wild_boar","snake"],
    "default":  ["elephant","tiger","lion","bear","wolf","leopard","hyena","jaguar","cougar","crocodile"]
}
DANGEROUS_CLASSES = REGION_ANIMAL_CLASSES
