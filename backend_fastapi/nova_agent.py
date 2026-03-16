import os
import boto3
import json
from typing import Optional, List

# Fetch region from environment, default to us-east-1 which supports Nova well
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
try:
    bedrock_client = boto3.client('bedrock-runtime', region_name=REGION)
except Exception as e:
    bedrock_client = None
    print(f"Failed to initialize bedrock client: {e}")

def analyze_incident_with_nova(image_bytes: bytes, animal_label: str, image_list: Optional[List[bytes]] = None, confidence: float = 0.0, source_model: str = "unknown", farm_lat: float = 0.0, farm_lon: float = 0.0, farm_region: str = "unknown", farmer_language: str = "en", active_threat_classes: Optional[List[str]] = None) -> dict:
    """
    Sends the specific frame(s) and prompt to Amazon Nova to generate a structured
    risk assessment and safety recommendation.
    """
    if not bedrock_client:
        return _fallback_response(animal_label, "Bedrock client not initialized.")

    analysis_context = "a sequence of snapshot images" if image_list and len(image_list) > 1 else "a snapshot image"
    
    system_prompt = f"""You are FarmGuard's threat assessment agent. You analyze wildlife detections on farms globally and make safety decisions.

Your job:
1. Confirm or deny the threat. If multiple images are provided, analyze the sequence to determine movement speed, direction, and posture changes relative to the perimeter.
2. Score severity 1-10 (10 = animal actively charging fence)
3. Compose an alert message in the farmer's language — be urgent and clear
4. Also provide English translation
5. Decide if neighboring farms (within 1km) should be alerted
6. Decide if a wildlife authority report should be filed

Behavior classification guide:
- GRAZING / RESTING: severity 3-4, monitor only
- MOVING TOWARD FENCE: severity 6-7, alert farmer
- AT FENCE / PUSHING: severity 8, alert farmer + neighbors  
- CHARGING / BREAKING THROUGH: severity 9-10, emergency all channels

Respond ONLY in valid JSON matching this schema:
{{
  "severity_score": int,
  "threat_confirmed": bool,
  "animal": str,
  "behavior": str,
  "reasoning": str,
  "alert_language": str,
  "farmer_message_local": str,
  "farmer_message_en": str,
  "neighbor_alert": bool,
  "neighbor_radius_km": float,
  "authority_report": bool,
  "recommended_action": str
}}

No markdown formatting, no explanation outside JSON.
"""
    
    user_input = f"""Analyze this {analysis_context} from a farm camera.
- Detection data: {animal_label} (Confidence: {confidence:.2f}, Detected by: {source_model})
- Farm location: {farm_region}, GPS: {farm_lat}, {farm_lon}
- Farmer's language preference: {farmer_language}
- Active threat classes for this region: {', '.join(active_threat_classes or [])}
"""

    # Construct message content
    content = []
    
    # Add multiple images if available
    images_to_use = image_list if image_list else [image_bytes]
    for img in images_to_use:
        content.append({
            "image": {
                "format": "jpeg",
                "source": {
                    "bytes": img
                }
            }
        })
    
    # Add text prompt (User input)
    content.append({
        "text": user_input
    })
    
    messages = [
        {
            "role": "user",
            "content": content
        }
    ]
    
    try:
        response = bedrock_client.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=messages,
            system=[{"text": system_prompt}],
            inferenceConfig={
                "maxTokens": 800,
                "temperature": 0.2
            }
        )
        
        output_text = response['output']['message']['content'][0]['text']
        
        # Parse JSON
        clean_text = output_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        parsed_json = json.loads(clean_text.strip())
        parsed_json["raw_nova_json"] = clean_text.strip()
        parsed_json["nova_prompt_input"] = user_input
        return parsed_json
        
    except json.JSONDecodeError as decode_err:
        print(f"Nova JSON parsing error: {decode_err} \nRaw output: {output_text}")
        return _fallback_response(animal_label, "AI analysis succeeded but failed to return valid JSON.")
    except Exception as e:
        print(f"Error calling Amazon Nova via Bedrock: {e}")
        return _fallback_response(animal_label, f"Bedrock API error.")

def _fallback_response(animal_label: str, reason: str = "") -> dict:
    """Provides a safe fallback response if Nova fails or is unavailable."""
    return {
        "severity_score": 7,
        "threat_confirmed": True,
        "animal": animal_label,
        "behavior": "unknown",
        "reasoning": f"Fallback alert activated ({reason}).",
        "alert_language": "en",
        "farmer_message_local": f"⚠️ Threat detected: {animal_label}. Seek shelter.",
        "farmer_message_en": f"⚠️ Threat detected: {animal_label}. Seek shelter.",
        "neighbor_alert": True,
        "neighbor_radius_km": 1.0,
        "authority_report": False,
        "recommended_action": "Stay indoors and secure the perimeter."
    }
