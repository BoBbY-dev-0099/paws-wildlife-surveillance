import boto3
import json
import base64
import numpy as np
from datetime import datetime
from config import (
    NOVA_MODEL_ID, NOVA_EMBED_MODEL_ID, NOVA_EMBED_FALLBACK_IDS, AWS_REGION
)

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

# Track which embed model ID works, so we only try once per session
_embed_resolved_model_id = None
_embed_all_failed = False


# ══ CALL 1: Nova 2 Lite — Visual threat analysis ══

def analyze_threat(image_b64: str, metadata: dict) -> dict:
    """
    Nova 2 Lite multimodal call. Image + farm context → structured JSON.
    Returns: threat_confirmed, animal, behavior, severity, deterrent_type,
             translations (6 languages), notify_authorities, reasoning,
             animal_count, behavior_description
    """
    region = metadata.get("region", "default")
    language = metadata.get("language", "en")

    system_prompt = f"""You are PAWS, an AI wildlife threat analyst for farm security.
Analyze this camera frame. Farm region: {region}.

Return ONLY valid JSON (no markdown):
{{
  "threat_confirmed": true/false,
  "animal": "species or null",
  "animal_count": number,
  "behavior": "charging|stalking|grazing|at_fence|fleeing|resting|unknown",
  "behavior_description": "one sentence describing exactly what the animal is doing",
  "severity": 1-10,
  "confidence": 0.0-1.0,
  "distance_estimate": "near|medium|far",
  "deterrent_type": "ultrasonic|strobe|siren|predator_audio|none",
  "deterrent_reasoning": "why this deterrent works for this species",
  "notify_authorities": true/false,
  "reasoning": "2-3 sentences explaining your threat assessment",
  "translations": {{
    "en": "⚠️ English alert (max 160 chars)",
    "hi": "⚠️ Hindi alert",
    "sw": "⚠️ Swahili alert",
    "es": "⚠️ Spanish alert",
    "pt": "⚠️ Portuguese alert",
    "ar": "⚠️ Arabic alert"
  }}
}}

Severity guide: 1-3=grazing far, 4-6=near perimeter, 7-9=at fence/aggressive, 10=breaching.
If no animal visible: threat_confirmed=false, severity=0."""

    try:
        response = bedrock.converse(
            modelId=NOVA_MODEL_ID,
            messages=[{
                "role": "user",
                "content": [
                    {"image": {"format": "jpeg", "source": {"bytes": base64.b64decode(image_b64)}}},
                    {"text": f"Farm region: {region}. YOLO detected: {metadata.get('label','unknown')} "
                             f"(conf: {metadata.get('confidence', 0):.2f}). Time: {datetime.now().isoformat()}"}
                ]
            }],
            system=[{"text": system_prompt}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
        )
        raw = response["output"]["message"]["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        result["model_used"] = NOVA_MODEL_ID
        return result

    except Exception as e:
        return {
            "threat_confirmed": True,
            "animal": metadata.get("label", "unknown"),
            "animal_count": 1,
            "behavior": "unknown",
            "behavior_description": "Nova analysis failed — defaulting to cautious alert",
            "severity": 6, "confidence": 0.5,
            "deterrent_type": "siren",
            "reasoning": f"Nova unavailable ({str(e)[:80]}). Defaulting to cautious alert.",
            "notify_authorities": False,
            "translations": {"en": f"⚠️ Possible {metadata.get('label','animal')} detected. Stay alert."},
            "model_used": "fallback",
            "error": str(e)
        }


# ══ CALL 2: Nova Embed — behavior description embedding ══

def get_behavior_embedding(text: str) -> list:
    """
    Nova Multimodal Embeddings — embeds behavior description text.
    Uses the correct taskType/singleEmbeddingParams payload format.
    Tries multiple model IDs if the first fails (ValidationException).
    Caches the working model ID for subsequent calls.
    """
    global _embed_resolved_model_id, _embed_all_failed

    if _embed_all_failed:
        return []

    # If we already know which model ID works, use it directly
    if _embed_resolved_model_id:
        return _invoke_embed(_embed_resolved_model_id, text)

    # Try each model ID in the fallback list
    for model_id in NOVA_EMBED_FALLBACK_IDS:
        try:
            result = _invoke_embed(model_id, text, raise_on_error=True)
            _embed_resolved_model_id = model_id
            print(f"[Nova Embed] Using model: {model_id}")
            return result
        except Exception as e:
            error_str = str(e)
            print(f"[Nova Embed] {model_id} failed: {error_str[:120]}")
            if "AccessDeniedException" in error_str:
                print(
                    f"[Nova Embed] Model {model_id} exists but access denied. "
                    "Enable it at: https://console.aws.amazon.com/bedrock/home#/modelaccess"
                )
            continue

    _embed_all_failed = True
    print("[Nova Embed] All model IDs exhausted. Embedding disabled for this session.")
    return []


def _invoke_embed(model_id: str, text: str, raise_on_error: bool = False) -> list:
    """Call the Nova embeddings API with the correct payload format."""
    request_body = {
        "taskType": "SINGLE_EMBEDDING",
        "singleEmbeddingParams": {
            "embeddingPurpose": "GENERIC_INDEX",
            "embeddingDimension": 384,
            "text": {
                "truncationMode": "END",
                "value": text
            }
        }
    }
    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        result = json.loads(response["body"].read())
        # Nova 2 Multimodal Embeddings returns: {"embeddings": [{"embedding": [...], "embeddingType": "TEXT"}]}
        embeddings_list = result.get("embeddings", [])
        if embeddings_list:
            return embeddings_list[0].get("embedding", [])
        return result.get("embedding", [])
    except Exception as e:
        if raise_on_error:
            raise
        return []


def find_similar_incidents(current_description: str, past_incidents: list) -> list:
    """
    Embed current incident description and compare to past incidents.
    Returns top 3 most similar with cosine similarity scores.
    """
    if not past_incidents:
        return []
    current_emb = get_behavior_embedding(current_description)
    if not current_emb:
        return []

    results = []
    for incident in past_incidents:
        past_emb = get_behavior_embedding(incident.get("description", ""))
        if past_emb:
            a, b = np.array(current_emb), np.array(past_emb)
            sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
            results.append({**incident, "similarity": round(sim, 4)})

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:3]


# ══ CALL 3: Nova 2 Lite — Incident report generation ══

def generate_incident_report(incident_data: dict) -> str:
    """
    Separate Nova 2 Lite call to write a professional incident narrative.
    This is the 3rd distinct Nova call per pipeline run.
    """
    try:
        prompt = f"""Generate a concise professional wildlife incident report:

Animal: {incident_data.get('animal','unknown')} ({incident_data.get('animal_count',1)} observed)
Behavior: {incident_data.get('behavior','unknown')} — {incident_data.get('behavior_description','')}
Severity: {incident_data.get('severity','N/A')}/10
Location: {incident_data.get('region','unknown')} (GPS: {incident_data.get('lat',0):.4f}, {incident_data.get('lon',0):.4f})
Time: {incident_data.get('timestamp','unknown')}
Deterrent activated: {incident_data.get('deterrent_type','none')}
Authorities notified: {incident_data.get('notify_authorities', False)}

Write a 3-4 sentence incident summary for the farm security log.
End with one recommended follow-up action."""

        response = bedrock.converse(
            modelId=NOVA_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 512, "temperature": 0.3}
        )
        return response["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"Report generation failed: {e}"


# ══ CALL 4: Amazon Polly — Voice alert (Nova Sonic fallback) ══

def generate_voice_alert(text: str, language: str = "en") -> str:
    """
    Generates spoken audio for the alert message using Amazon Polly neural voices.
    Nova Sonic is speech-to-speech (not pure TTS), so Polly is the correct AWS
    service for farmer voice alerts. Returns base64-encoded MP3.

    Language support: en, hi, es, pt, sw (fallback to en for unsupported)
    """
    polly = boto3.client("polly", region_name=AWS_REGION)

    VOICE_MAP = {
        "en": ("Matthew", "en-US"),
        "hi": ("Aditi",   "hi-IN"),
        "es": ("Miguel",  "es-US"),
        "pt": ("Cristiano","pt-BR"),
        "sw": ("Matthew", "en-US"),  # Swahili fallback
        "ar": ("Zeina",   "arb"),
        "pl": ("Ewa",     "pl-PL"),
    }
    voice_id, lang_code = VOICE_MAP.get(language, ("Matthew", "en-US"))

    try:
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice_id,
            Engine="neural" if voice_id not in ["Aditi", "Zeina"] else "standard",
            LanguageCode=lang_code
        )
        audio_bytes = response["AudioStream"].read()
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[Polly] Voice generation failed: {e}")
        return ""
