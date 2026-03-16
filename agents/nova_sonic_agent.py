"""
Nova Sonic Agent - Real-time voice interaction for farmers.

Nova Sonic ONLY supports InvokeModelWithBidirectionalStream, which is NOT
in boto3.  It requires the aws_sdk_bedrock_runtime package (Python 3.12+).

When the SDK is unavailable we fall back to Nova Lite (text) + Polly (TTS).
The Polly fallback does NOT understand spoken queries — it generates a
proactive farm-status response instead.

Audio format pipeline:
  Telegram voice (OGG/Opus) -> ffmpeg -> raw LPCM 16 kHz mono -> Sonic
  Sonic output (LPCM 24 kHz mono) -> ffmpeg -> OGG/Opus -> Telegram sendVoice
"""

import boto3
import json
import base64
import uuid
import httpx
import io
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from config import AWS_REGION, NOVA_SONIC_MODEL_ID

bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
TELEGRAM_BOT_TOKEN = ""

_HAS_SONIC_SDK = False

if sys.version_info >= (3, 12):
    try:
        from aws_sdk_bedrock_runtime.client import (
            BedrockRuntimeClient,
            InvokeModelWithBidirectionalStreamOperationInput,
        )
        from aws_sdk_bedrock_runtime.models import (
            InvokeModelWithBidirectionalStreamInputChunk,
            BidirectionalInputPayloadPart,
        )
        from aws_sdk_bedrock_runtime.config import (
            Config as SonicConfig,
            HTTPAuthSchemeResolver,
            SigV4AuthScheme,
        )
        from smithy_aws_core.credentials_resolvers.environment import (
            EnvironmentCredentialsResolver,
        )
        _HAS_SONIC_SDK = True
        print("[SONIC] Bidirectional streaming SDK loaded (aws_sdk_bedrock_runtime)")
    except ImportError:
        pass

if not _HAS_SONIC_SDK:
    reason = (
        f"Python {sys.version_info.major}.{sys.version_info.minor} (need 3.12+)"
        if sys.version_info < (3, 12)
        else "aws_sdk_bedrock_runtime not installed"
    )
    print(f"[SONIC] {reason}. Voice alerts via Nova Lite + Polly.")
    print("[SONIC] For real Sonic: Python 3.12+ and pip install aws_sdk_bedrock_runtime")


def set_telegram_token(token: str):
    global TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN = token


# ─────────────────────────────────────────────────────
# Audio transcoding helpers (ffmpeg)
# ─────────────────────────────────────────────────────

def _ogg_to_pcm16k(ogg_bytes: bytes) -> bytes:
    """Telegram OGG/Opus -> raw LPCM s16le 16 kHz mono (what Sonic expects)."""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "input.ogg"
        dst = Path(td) / "output.raw"
        src.write_bytes(ogg_bytes)
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ac", "1", "-ar", "16000",
                "-f", "s16le", str(dst),
            ],
            check=True, capture_output=True,
        )
        return dst.read_bytes()


def _lpcm24k_to_ogg(pcm_bytes: bytes) -> bytes:
    """Sonic LPCM s16le 24 kHz mono -> OGG/Opus (what Telegram sendVoice expects)."""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "input.raw"
        dst = Path(td) / "output.ogg"
        src.write_bytes(pcm_bytes)
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(src),
                "-c:a", "libopus", "-b:a", "32k",
                str(dst),
            ],
            check=True, capture_output=True,
        )
        return dst.read_bytes()


# ─────────────────────────────────────────────────────
# Sonic SDK client builder
# ─────────────────────────────────────────────────────

def _build_sonic_client():
    """Construct a BedrockRuntimeClient with current Nova 2 auth config."""
    config = SonicConfig(
        endpoint_uri=f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com",
        region=AWS_REGION,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        auth_scheme_resolver=HTTPAuthSchemeResolver(),
        auth_schemes={"aws.auth#sigv4": SigV4AuthScheme(service="bedrock")},
    )
    return BedrockRuntimeClient(config=config)


# ─────────────────────────────────────────────────────
# Download voice from Telegram
# ─────────────────────────────────────────────────────

async def download_telegram_voice(file_id: str) -> bytes:
    """Returns raw OGG/Opus bytes from a Telegram voice message."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("Telegram bot token not configured")

    TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{TG_API}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        audio_resp = await client.get(file_url)
        audio_resp.raise_for_status()
        return audio_resp.content


# ─────────────────────────────────────────────────────
# Process farmer voice query
# ─────────────────────────────────────────────────────

async def process_voice_with_sonic(
    audio_bytes: bytes,
    farm_context: dict,
) -> dict:
    """
    audio_bytes: OGG/Opus from Telegram.
    If Sonic SDK is present: transcode to LPCM, run Sonic, transcode back to OGG.
    Otherwise: ignore audio, generate a status response with Nova Lite + Polly.
    """
    region = farm_context.get("region", "unknown")
    active_threats = farm_context.get("active_threats", 0)
    recent = farm_context.get("recent_incidents", [])
    language = farm_context.get("language", "en")

    status_context = f"Farm region: {region}. Active threats: {active_threats}. "
    if recent:
        latest = recent[0]
        status_context += (
            f"Most recent: {latest.get('animal', 'unknown')} detected "
            f"{latest.get('minutes_ago', '?')} minutes ago, "
            f"severity {latest.get('severity', '?')}/10. "
        )
    else:
        status_context += "No recent incidents. All perimeters clear. "

    system_prompt = (
        "You are PAWS, an AI wildlife security assistant. "
        "A farmer is asking you about their farm's safety status. "
        "Respond in short, clear sentences. Be reassuring but honest. "
        "If there are active threats, be specific about animal, location, severity. "
        "If all clear, confirm that monitoring is active.\n\n"
        f"CURRENT STATUS:\n{status_context}"
    )

    if _HAS_SONIC_SDK:
        try:
            pcm_audio = _ogg_to_pcm16k(audio_bytes)
            return await _sonic_bidirectional(pcm_audio, system_prompt, language)
        except Exception as e:
            print(f"[SONIC] Bidirectional stream failed: {e}")

    return await _fallback_nova_lite_polly(system_prompt, farm_context)


# ─────────────────────────────────────────────────────
# Real Sonic path (Python 3.12+ with SDK)
# ─────────────────────────────────────────────────────

async def _sonic_bidirectional(
    pcm_audio: bytes, system_prompt: str, language: str,
) -> dict:
    """
    pcm_audio: raw LPCM s16le 16 kHz mono (already transcoded from OGG).
    Returns dict with audio_b64 in OGG/Opus format ready for Telegram.
    """
    client = _build_sonic_client()
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(
            model_id=NOVA_SONIC_MODEL_ID
        )
    )

    prompt_name = str(uuid.uuid4())
    text_content_name = str(uuid.uuid4())
    audio_content_name = str(uuid.uuid4())

    lang_map = {"en": "en-US", "hi": "hi-IN", "es": "es-US", "pt": "pt-BR", "sw": "en-US"}
    sonic_lang = lang_map.get(language, "en-US")

    async def send_evt(payload: dict):
        raw = json.dumps(payload)
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=raw.encode("utf-8"))
        )
        await stream.input_stream.send(chunk)

    # 1. Session start
    await send_evt({"event": {"sessionStart": {
        "inferenceConfiguration": {"maxTokens": 512, "topP": 0.9, "temperature": 0.7},
    }}})

    # 2. Prompt start with output config
    await send_evt({"event": {"promptStart": {
        "promptName": prompt_name,
        "textOutputConfiguration": {"mediaType": "text/plain"},
        "audioOutputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": 24000,
            "sampleSizeBits": 16,
            "channelCount": 1,
            "voiceId": "matthew",
            "encoding": "base64",
            "audioType": "SPEECH",
        },
    }}})

    # 3. System prompt (TEXT, SYSTEM role)
    await send_evt({"event": {"contentStart": {
        "promptName": prompt_name,
        "contentName": text_content_name,
        "type": "TEXT", "interactive": True, "role": "SYSTEM",
        "textInputConfiguration": {"mediaType": "text/plain"},
    }}})
    await send_evt({"event": {"textInput": {
        "promptName": prompt_name,
        "contentName": text_content_name,
        "content": system_prompt,
    }}})
    await send_evt({"event": {"contentEnd": {
        "promptName": prompt_name,
        "contentName": text_content_name,
    }}})

    # 4. Audio input (AUDIO, USER role) — already LPCM 16 kHz mono
    await send_evt({"event": {"contentStart": {
        "promptName": prompt_name,
        "contentName": audio_content_name,
        "type": "AUDIO", "interactive": True, "role": "USER",
        "audioInputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": 16000,
            "sampleSizeBits": 16,
            "channelCount": 1,
            "audioType": "SPEECH",
            "encoding": "base64",
        },
    }}})
    audio_b64 = base64.b64encode(pcm_audio).decode("utf-8")
    await send_evt({"event": {"audioInput": {
        "promptName": prompt_name,
        "contentName": audio_content_name,
        "content": audio_b64,
    }}})
    await send_evt({"event": {"contentEnd": {
        "promptName": prompt_name,
        "contentName": audio_content_name,
    }}})

    # 5. Close
    await send_evt({"event": {"promptEnd": {"promptName": prompt_name}}})
    await send_evt({"event": {"sessionEnd": {}}})
    await stream.input_stream.close()

    # 6. Collect responses, tracking contentStart role
    audio_chunks: list[bytes] = []
    transcript_out = ""
    transcript_in = ""
    current_role = None

    try:
        while True:
            output = await stream.await_output()
            result = await output[1].receive()
            if not (result.value and result.value.bytes_):
                continue
            data = json.loads(result.value.bytes_.decode("utf-8"))
            evt = data.get("event", {})

            if "contentStart" in evt:
                current_role = evt["contentStart"].get("role")

            elif "textOutput" in evt:
                text = evt["textOutput"].get("content", "")
                if current_role == "USER":
                    transcript_in += text
                elif current_role == "ASSISTANT":
                    transcript_out += text

            elif "audioOutput" in evt:
                audio_chunks.append(
                    base64.b64decode(evt["audioOutput"]["content"])
                )
    except Exception:
        pass

    # 7. Transcode LPCM 24 kHz -> OGG/Opus for Telegram
    raw_pcm = b"".join(audio_chunks)
    ogg_bytes = b""
    if raw_pcm:
        try:
            ogg_bytes = _lpcm24k_to_ogg(raw_pcm)
        except Exception as e:
            print(f"[SONIC] LPCM->OGG transcode failed: {e}")

    ogg_b64 = base64.b64encode(ogg_bytes).decode() if ogg_bytes else ""
    print(f"[SONIC] Bidirectional done. Chunks: {len(audio_chunks)}, "
          f"transcript_in: {len(transcript_in)} chars, transcript_out: {len(transcript_out)} chars")

    return {
        "audio_b64": ogg_b64,
        "audio_format": "ogg",
        "transcript_in": transcript_in,
        "transcript_out": transcript_out,
        "model": NOVA_SONIC_MODEL_ID,
        "success": bool(ogg_b64),
        "sonic_attempted": True,
    }


# ─────────────────────────────────────────────────────
# Polly fallback (Python <3.12 or SDK missing)
# ─────────────────────────────────────────────────────

async def _fallback_nova_lite_polly(
    system_prompt: str,
    farm_context: dict,
) -> dict:
    """
    No ASR available without Sonic. We ignore the farmer's spoken words and
    generate a proactive farm-status response via Nova Lite, then Polly TTS.
    Output is OGG/Vorbis — Telegram-native.
    """
    recent = farm_context.get("recent_incidents", [])
    region = farm_context.get("region", "unknown")
    language = farm_context.get("language", "en")

    try:
        from config import NOVA_MODEL_ID

        prompt = (
            "A farmer just sent a voice message asking about their farm's status. "
            "Generate a brief, spoken response (2-4 sentences) they would hear. "
            "Be conversational, not robotic.\n\n"
            f"Farm region: {region}\n"
            f"Active threats: {farm_context.get('active_threats', 0)}\n"
        )
        if recent:
            prompt += "Recent incidents:\n"
            for inc in recent[:3]:
                prompt += (
                    f"- {inc.get('animal', '?')}, severity {inc.get('severity', '?')}, "
                    f"{inc.get('minutes_ago', '?')} min ago\n"
                )
        else:
            prompt += "No recent incidents.\n"
        prompt += f"\nRespond in {language}. Speak naturally."

        nova_resp = bedrock_runtime.converse(
            modelId=NOVA_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[{"text": system_prompt}],
            inferenceConfig={"maxTokens": 256, "temperature": 0.5},
        )
        response_text = nova_resp["output"]["message"]["content"][0]["text"]
    except Exception:
        if farm_context.get("active_threats", 0) > 0:
            response_text = "PAWS is monitoring an active threat. Stay alert."
        else:
            response_text = "All clear. PAWS is monitoring your farm. No threats detected."

    audio_b64 = ""
    try:
        polly = boto3.client("polly", region_name=AWS_REGION)
        voice_map = {
            "en": "Matthew", "hi": "Aditi", "es": "Miguel",
            "pt": "Cristiano", "fr": "Mathieu", "sw": "Matthew",
        }
        polly_resp = polly.synthesize_speech(
            Text=response_text,
            OutputFormat="ogg_vorbis",
            VoiceId=voice_map.get(language, "Matthew"),
            Engine="neural" if voice_map.get(language, "Matthew") not in ["Aditi"] else "standard",
        )
        audio_b64 = base64.b64encode(polly_resp["AudioStream"].read()).decode()
    except Exception as polly_err:
        print(f"[POLLY] Error: {polly_err}")

    return {
        "audio_b64": audio_b64,
        "audio_format": "ogg",
        "transcript_in": "(no ASR without Sonic SDK - responded with farm status)",
        "transcript_out": response_text,
        "model": "nova-lite + polly",
        "sonic_attempted": True,
        "is_fallback": True,
        "success": bool(audio_b64),
    }


# ─────────────────────────────────────────────────────
# Send voice response back via Telegram
# ─────────────────────────────────────────────────────

async def send_telegram_voice(
    chat_id: int,
    audio_b64: str,
    caption: str = "",
    audio_format: str = "ogg",
):
    """
    audio_format: "ogg" means ready for Telegram; "lpcm" will be transcoded first.
    Both Sonic-path (now outputs ogg) and Polly-path output ogg, but this
    handles the edge case where a caller passes raw LPCM.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("[Telegram] Bot token not configured, skipping voice send")
        return

    TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    if not audio_b64:
        async with httpx.AsyncClient() as client:
            await client.post(f"{TG_API}/sendMessage", json={
                "chat_id": chat_id,
                "text": f"PAWS: {caption}" if caption else "Voice response unavailable.",
            })
        return

    audio_bytes = base64.b64decode(audio_b64)

    if audio_format == "lpcm":
        try:
            audio_bytes = _lpcm24k_to_ogg(audio_bytes)
        except Exception as e:
            print(f"[Telegram] LPCM->OGG transcode failed: {e}")
            async with httpx.AsyncClient() as client:
                await client.post(f"{TG_API}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": f"PAWS: {caption}" if caption else "Voice encoding failed.",
                })
            return

    async with httpx.AsyncClient(timeout=30) as client:
        files = {"voice": ("response.ogg", io.BytesIO(audio_bytes), "audio/ogg")}
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
        resp = await client.post(f"{TG_API}/sendVoice", data=data, files=files)
        resp.raise_for_status()


# ─────────────────────────────────────────────────────
# Generate proactive voice alert (called by pipeline)
# ─────────────────────────────────────────────────────

async def generate_threat_voice_alert(
    incident_data: dict, language: str = "en",
) -> dict:
    """
    Pipeline step: generate a spoken warning for a confirmed threat.
    Sonic SDK -> bidirectional TTS, or Polly fallback.
    Always returns audio_format="ogg" ready for Telegram.
    """
    animal = incident_data.get("animal", "unknown")
    severity = incident_data.get("severity", 5)
    behavior = incident_data.get("behavior", "unknown")

    if severity >= 8:
        script = (
            f"Urgent alert! A {animal} has been detected very close to your farm. "
            f"It appears to be {behavior}. Threat level is {severity} out of 10. "
            f"Please secure all livestock and stay indoors immediately. "
            f"Authorities have been notified."
        )
    elif severity >= 5:
        script = (
            f"Warning. A {animal} has been spotted near your farm perimeter. "
            f"The animal is {behavior}. Threat level is {severity} out of 10. "
            f"Please keep children and animals inside. Monitoring continues."
        )
    else:
        script = (
            f"Notice. A {animal} was detected in your area. "
            f"It appears to be {behavior} at a safe distance. "
            f"Threat level is low at {severity} out of 10. "
            f"No immediate action required. PAWS continues monitoring."
        )

    if _HAS_SONIC_SDK:
        try:
            result = await _sonic_tts(script, language)
            if result.get("success"):
                return result
        except Exception as e:
            print(f"[SONIC] TTS failed, using Polly: {e}")

    print("[SONIC] Using Polly for voice alert")
    try:
        polly = boto3.client("polly", region_name=AWS_REGION)
        voice_map = {"en": "Matthew", "hi": "Aditi", "es": "Miguel", "pt": "Cristiano"}
        resp = polly.synthesize_speech(
            Text=script,
            OutputFormat="ogg_vorbis",
            VoiceId=voice_map.get(language, "Matthew"),
            Engine="neural" if voice_map.get(language, "Matthew") != "Aditi" else "standard",
        )
        audio = resp["AudioStream"].read()
        return {
            "audio_b64": base64.b64encode(audio).decode(),
            "audio_format": "ogg",
            "transcript": script,
            "model": "polly",
            "sonic_attempted": True,
            "is_fallback": True,
            "success": True,
        }
    except Exception as polly_err:
        return {
            "audio_b64": "",
            "audio_format": "ogg",
            "transcript": script,
            "model": "none",
            "sonic_attempted": True,
            "success": False,
            "error": str(polly_err),
        }


async def _sonic_tts(script: str, language: str) -> dict:
    """Sonic bidirectional TTS: text in -> LPCM out -> OGG/Opus for Telegram."""
    client = _build_sonic_client()
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(
            model_id=NOVA_SONIC_MODEL_ID
        )
    )

    prompt_name = str(uuid.uuid4())
    content_name = str(uuid.uuid4())

    lang_map = {"en": "en-US", "hi": "hi-IN", "es": "es-US", "pt": "pt-BR", "sw": "en-US"}
    sonic_lang = lang_map.get(language, "en-US")

    async def send_evt(payload: dict):
        raw = json.dumps(payload)
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=raw.encode("utf-8"))
        )
        await stream.input_stream.send(chunk)

    await send_evt({"event": {"sessionStart": {
        "inferenceConfiguration": {"maxTokens": 256, "temperature": 0.3},
    }}})

    await send_evt({"event": {"promptStart": {
        "promptName": prompt_name,
        "textOutputConfiguration": {"mediaType": "text/plain"},
        "audioOutputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": 24000,
            "sampleSizeBits": 16,
            "channelCount": 1,
            "voiceId": "matthew",
            "encoding": "base64",
            "audioType": "SPEECH",
        },
    }}})

    await send_evt({"event": {"contentStart": {
        "promptName": prompt_name,
        "contentName": content_name,
        "type": "TEXT", "interactive": True, "role": "USER",
        "textInputConfiguration": {"mediaType": "text/plain"},
    }}})
    await send_evt({"event": {"textInput": {
        "promptName": prompt_name,
        "contentName": content_name,
        "content": f"Read this alert out loud clearly: {script}",
    }}})
    await send_evt({"event": {"contentEnd": {
        "promptName": prompt_name,
        "contentName": content_name,
    }}})

    await send_evt({"event": {"promptEnd": {"promptName": prompt_name}}})
    await send_evt({"event": {"sessionEnd": {}}})
    await stream.input_stream.close()

    audio_chunks: list[bytes] = []
    try:
        while True:
            output = await stream.await_output()
            result = await output[1].receive()
            if not (result.value and result.value.bytes_):
                continue
            data = json.loads(result.value.bytes_.decode("utf-8"))
            evt = data.get("event", {})
            if "audioOutput" in evt:
                audio_chunks.append(
                    base64.b64decode(evt["audioOutput"]["content"])
                )
    except Exception:
        pass

    raw_pcm = b"".join(audio_chunks)
    ogg_bytes = b""
    if raw_pcm:
        try:
            ogg_bytes = _lpcm24k_to_ogg(raw_pcm)
        except Exception as e:
            print(f"[SONIC] LPCM->OGG transcode failed: {e}")

    ogg_b64 = base64.b64encode(ogg_bytes).decode() if ogg_bytes else ""
    print(f"[SONIC] TTS done. Audio chunks: {len(audio_chunks)}")

    return {
        "audio_b64": ogg_b64,
        "audio_format": "ogg",
        "transcript": script,
        "model": NOVA_SONIC_MODEL_ID,
        "sonic_attempted": True,
        "success": bool(ogg_b64),
    }
