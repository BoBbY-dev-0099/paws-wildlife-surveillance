import time, json, base64, traceback, threading, asyncio
from datetime import datetime
from config import (
    DANGEROUS_CLASSES, DETECTION_COOLDOWN_SECONDS, ALERT_SEVERITY_THRESHOLD,
    DETERRENT_SEVERITY_THRESHOLD, AUTHORITY_SEVERITY_THRESHOLD, gps_to_region
)
from agents.nova_agent import (
    analyze_threat, get_behavior_embedding, find_similar_incidents,
    generate_incident_report
)
from agents.nova_sonic_agent import generate_threat_voice_alert, send_telegram_voice
from agents.nova_act_agent import file_wildlife_report, get_regional_advisories
from agents.alert_agent import dispatch_all_alerts, cascade_neighbor_alerts
from agents.dataset_agent import save_to_dataset
from agents.deterrent_agent import trigger_deterrent
from models.incident import SessionLocal, Incident, IncidentStatus
from sse import nova_sse

_last_detections = {}  # in-memory debounce


def _run_async(coro):
    """
    Safely run async function from a sync background thread.
    CRITICAL: Pipeline runs in threading.Thread — must create new event loop.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_detection_pipeline(label, confidence, image_b64, bbox=None,
                           source_model="yolo-world", cam_id="default", farm_config=None):
    """
    14-step pipeline. Every step publishes SSE.
    Called from background thread (never blocks main FastAPI thread).
    """
    start = time.time()
    pipeline_id = f"pipe_{int(start*1000)}"
    farm_config = farm_config or {}
    region = farm_config.get("region", gps_to_region(
        farm_config.get("lat", 0), farm_config.get("lon", 0)))
    language = farm_config.get("language", "en")

    def sse(step, msg, data=None):
        nova_sse.publish({
            "pipeline_id": pipeline_id,
            "camera_id": cam_id,
            "step": step,
            "message": msg,
            "data": data or {},
            "elapsed_ms": int((time.time() - start) * 1000),
            "timestamp": datetime.utcnow().isoformat()
        })

    db = SessionLocal()
    incident_id = None

    try:
        # ── 1. Gate ────────────────────────────────────────────────────────────
        sse("gate", f"Received: {label} ({confidence:.0%}) from {source_model}")
        dangerous = [d.lower() for d in DANGEROUS_CLASSES.get(region, DANGEROUS_CLASSES["default"])]
        if label.lower() not in dangerous:
            sse("gate", f"'{label}' not a threat in {region}. Saving as non_threat.")
            save_to_dataset(image_b64, label, confidence, bbox, "non_threat", {"region": region})
            sse("complete", "Pipeline done — non_threat", {"status": "non_threat"})
            return

        # ── 2. Debounce ────────────────────────────────────────────────────────
        key = f"{cam_id}:{label}"
        now = time.time()
        if now - _last_detections.get(key, 0) < DETECTION_COOLDOWN_SECONDS:
            sse("debounce", f"Within {DETECTION_COOLDOWN_SECONDS}s cooldown. Skipping.")
            sse("complete", "Pipeline done — debounced", {"status": "debounced"})
            return
        _last_detections[key] = now
        sse("debounce", "Cooldown passed.")

        # ── 3. Create DB incident ──────────────────────────────────────────────
        incident = Incident(
            animal=label, confidence=confidence, camera_id=cam_id,
            region=region, status=IncidentStatus.ANALYZING,
            source_model=source_model, created_at=datetime.utcnow(),
            image_b64=image_b64[:200] + "..." if image_b64 else None,
            bbox=json.dumps(bbox) if bbox else None
        )
        db.add(incident); db.commit(); db.refresh(incident)
        incident_id = incident.id
        sse("db", f"Incident #{incident_id} created.", {"incident_id": incident_id})

        # ── 4. NOVA CALL 1: Threat analysis ───────────────────────────────────
        sse("nova_lite", "🧠 Nova 2 Lite analyzing threat...")
        nova_result = analyze_threat(image_b64, {
            "label": label, "confidence": confidence,
            "region": region, "language": language,
            "lat": farm_config.get("lat", 0), "lon": farm_config.get("lon", 0)
        })
        
        # Enhanced SSE with full Nova response
        sse("nova_lite",
            f"✅ Nova Analysis Complete: threat={nova_result.get('threat_confirmed')}, "
            f"severity={nova_result.get('severity')}/10, behavior={nova_result.get('behavior')}",
            {
                "nova_full_response": nova_result,
                "reasoning": nova_result.get('reasoning', ''),
                "behavior_description": nova_result.get('behavior_description', ''),
                "deterrent_type": nova_result.get('deterrent_type', 'none')
            })

        # ── 5. NOVA CALL 2: Embeddings ─────────────────────────────────────────
        sse("embeddings", "🔗 Nova Embeddings generating vector...")
        behavior_desc = (
            f"{nova_result.get('animal', label)} {nova_result.get('behavior', 'unknown')} "
            f"in {region}, severity {nova_result.get('severity', 0)}. "
            f"{nova_result.get('behavior_description', '')}"
        )
        embedding = get_behavior_embedding(behavior_desc)
        past = [
            {"id": p.id, "description": f"{p.animal} {p.nova_behavior or ''} sev {p.nova_severity or 0}",
             "animal": p.animal, "severity": p.nova_severity}
            for p in db.query(Incident).filter(
                Incident.id != incident_id,
                Incident.status == IncidentStatus.ALERTED
            ).order_by(Incident.created_at.desc()).limit(20).all()
        ]
        similar = find_similar_incidents(behavior_desc, past) if past else []
        sse("embeddings",
            f"✅ Embedding Complete: {len(embedding)}D vector generated. Found {len(similar)} similar past incidents.",
            {
                "embedding_dims": len(embedding), 
                "similar_incidents": similar,
                "behavior_description": behavior_desc,
                "model": "amazon.nova-2-multimodal-embeddings-v1:0"
            })

        # ── 6. Decision gate ───────────────────────────────────────────────────
        if not nova_result.get("threat_confirmed", False):
            sse("decision", "Nova dismissed threat. Not alerting.")
            incident.status = IncidentStatus.DISMISSED
            incident.nova_threat_confirmed = False
            incident.nova_severity = nova_result.get("severity", 0)
            incident.nova_behavior = nova_result.get("behavior")
            incident.nova_reasoning = nova_result.get("reasoning")
            incident.nova_raw_json = json.dumps(nova_result)
            incident.embedding_dims = len(embedding)
            incident.pipeline_ms = int((time.time() - start) * 1000)
            db.commit()
            save_to_dataset(image_b64, label, confidence, bbox, "nova_rejected", {"region": region})
            sse("complete", "Pipeline done — dismissed", {"status": "dismissed", "incident_id": incident_id})
            return

        severity = nova_result.get("severity", 5)
        sse("decision", f"⚠️ THREAT CONFIRMED. Severity {severity}/10.")

        # ── 7. NOVA CALL 3: Incident report generation ─────────────────────────
        sse("nova_report", "📝 Nova 2 Lite generating incident report...")
        report = generate_incident_report({
            "animal": nova_result.get("animal", label),
            "animal_count": nova_result.get("animal_count", 1),
            "behavior": nova_result.get("behavior"),
            "behavior_description": nova_result.get("behavior_description", ""),
            "severity": severity, "region": region,
            "lat": farm_config.get("lat", 0), "lon": farm_config.get("lon", 0),
            "timestamp": datetime.utcnow().isoformat(),
            "deterrent_type": nova_result.get("deterrent_type", "none"),
            "notify_authorities": nova_result.get("notify_authorities", False)
        })
        sse("nova_report", 
            f"✅ Report Generated ({len(report)} chars)", 
            {
                "report_full": report,
                "report_preview": report[:300] + "..." if len(report) > 300 else report,
                "model": "us.amazon.nova-lite-v1:0"
            })

        # ── 8. Nova Sonic Voice Alert ──────────────────────────────────────────
        sse("sonic", "🔊 Nova Sonic generating voice alert...")
        sonic_result = _run_async(generate_threat_voice_alert(
            incident_data={
                "animal": nova_result.get("animal", label),
                "severity": severity,
                "behavior": nova_result.get("behavior", "unknown"),
                "confidence": confidence
            },
            language=language
        ))
        
        voice_model = sonic_result.get("model", "none")
        has_voice = sonic_result.get("success", False)
        sonic_attempted = sonic_result.get("sonic_attempted", True)
        voice_b64 = sonic_result.get("audio_b64", "")
        transcript = sonic_result.get("transcript", "")
        
        sse("sonic", 
            f"✅ Voice Alert Generated: model={voice_model}, audio={'yes' if has_voice else 'no'}",
            {
                "model": voice_model, 
                "has_audio": has_voice, 
                "sonic_attempted": sonic_attempted,
                "transcript_full": transcript,
                "transcript_preview": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "audio_format": sonic_result.get("audio_format", "ogg_vorbis")
            })
        
        # ── 9. Nova Act — File Report + Scrape Advisories ──────────────────────
        act_report = {}
        advisories = {}
        if severity >= 7:
            sse("nova_act", "🤖 Nova Act filing report on wildlife portal...")
            
            act_report = _run_async(file_wildlife_report({
                "animal": nova_result.get("animal", label),
                "severity": severity,
                "behavior": nova_result.get("behavior"),
                "region": region,
                "lat": farm_config.get("lat", 0),
                "lon": farm_config.get("lon", 0),
                "confidence": confidence
            }))
            
            sse("nova_act", 
                f"✅ Report {'Successfully Filed' if act_report.get('success') else 'Failed'} → "
                f"{act_report.get('portal', 'unknown portal')}",
                {
                    "report_full_result": act_report,
                    "confirmation_number": act_report.get('confirmation_number', 'N/A'),
                    "workflow_steps": act_report.get('steps', [])
                })
            
            # Scrape advisories
            sse("nova_act", "🤖 Nova Act scraping regional wildlife advisories...")
            
            advisories = _run_async(get_regional_advisories(
                region, farm_config.get("lat", 0), farm_config.get("lon", 0)
            ))
            
            advisory_count = len(advisories.get("advisories", []))
            sse("nova_act", 
                f"✅ Found {advisory_count} recent wildlife advisories in {region}",
                {
                    "advisories_full": advisories,
                    "advisory_list": advisories.get("advisories", [])[:5]  # First 5
                })
        else:
            sse("nova_act", f"⏭️ Severity {severity} < 7. Skipping Nova Act (portal filing).")

        # ── 10. Save to training dataset ───────────────────────────────────────
        sse("dataset", "💾 Saving detection to training dataset...")
        save_to_dataset(image_b64, label, confidence, bbox, "confirmed_threat", {
            "region": region, "nova_severity": severity,
            "nova_behavior": nova_result.get("behavior"),
            "embedding_dims": len(embedding)
        })
        sse("dataset", f"✅ Saved to dataset/ as confirmed_threat")

        # ── 11. Dispatch alerts (ntfy + Telegram) ─────────────────────────────
        alerts_sent = {}
        if severity >= ALERT_SEVERITY_THRESHOLD:
            sse("alerts", f"📡 Dispatching alerts (severity {severity} >= threshold {ALERT_SEVERITY_THRESHOLD})...")
            alerts_sent = dispatch_all_alerts(
                incident_id=incident_id,
                animal=nova_result.get("animal", label),
                severity=severity,
                behavior=nova_result.get("behavior", "unknown"),
                image_b64=image_b64,
                translations=nova_result.get("translations", {}),
                region=region, language=language, voice_b64=voice_b64
            )
            sse("alerts", 
                f"✅ Alerts dispatched: ntfy={'✓' if alerts_sent.get('ntfy') else '✗'}, "
                f"telegram={'✓' if alerts_sent.get('telegram') else '✗'}",
                {"alerts_sent": alerts_sent})
        else:
            sse("alerts", f"⏭️ Severity {severity} < {ALERT_SEVERITY_THRESHOLD}. Skipping alerts.")

        # ── 12. Community mesh cascade ─────────────────────────────────────────
        neighbor_count = 0
        if severity >= 7:
            sse("mesh", "🌐 Cascading to neighbor farms...")
            neighbor_count = cascade_neighbor_alerts(
                animal=nova_result.get("animal", label), severity=severity,
                region=region, lat=farm_config.get("lat", 0),
                lon=farm_config.get("lon", 0),
                radius_km=farm_config.get("neighbor_radius", 15)
            )
            sse("mesh", f"Notified {neighbor_count} neighbor farms.", {"neighbors": neighbor_count})

        # ── 13. Deterrent ──────────────────────────────────────────────────────
        deterrent_fired = False
        if severity >= DETERRENT_SEVERITY_THRESHOLD and nova_result.get("deterrent_type", "none") != "none":
            sse("deterrent", f"🚨 Triggering: {nova_result['deterrent_type']}...")
            deterrent_fired = trigger_deterrent(nova_result["deterrent_type"])
            sse("deterrent", f"Deterrent {'fired' if deterrent_fired else 'failed'}")

        # ── 14. Authority notification ─────────────────────────────────────────
        authority_notified = False
        if severity >= AUTHORITY_SEVERITY_THRESHOLD and nova_result.get("notify_authorities"):
            sse("authority", "🏛️ Notifying wildlife authorities...")
            authority_notified = _notify_authorities_ntfy(region, nova_result, incident_id)
            sse("authority", f"Authorities {'notified' if authority_notified else 'failed'}")

        # ── 15. Update DB + final SSE ──────────────────────────────────────────
        pipeline_ms = int((time.time() - start) * 1000)
        incident.status = IncidentStatus.ALERTED
        incident.nova_threat_confirmed = True
        incident.nova_severity = severity
        incident.nova_behavior = nova_result.get("behavior")
        incident.nova_animal = nova_result.get("animal")
        incident.nova_animal_count = nova_result.get("animal_count", 1)
        incident.nova_behavior_description = nova_result.get("behavior_description")
        incident.nova_reasoning = nova_result.get("reasoning")
        incident.nova_deterrent_type = nova_result.get("deterrent_type")
        incident.nova_raw_json = json.dumps(nova_result)
        incident.nova_report = report
        incident.embedding_dims = len(embedding)
        incident.similar_incidents = json.dumps(similar)
        incident.alerts_sent = json.dumps(alerts_sent)
        incident.neighbors_notified = neighbor_count
        incident.authority_notified = authority_notified
        incident.deterrent_fired = deterrent_fired
        incident.has_voice_alert = bool(voice_b64)
        incident.voice_model = voice_model
        incident.sonic_attempted = sonic_attempted
        incident.nova_act_report = json.dumps(act_report) if act_report else None
        incident.advisories = json.dumps(advisories) if advisories else None
        incident.pipeline_ms = pipeline_ms
        db.commit()

        sse("complete", "✅ Pipeline complete", {
            "status": "alerted", "incident_id": incident_id,
            "animal": nova_result.get("animal", label), "severity": severity,
            "behavior": nova_result.get("behavior"), "pipeline_ms": pipeline_ms,
            "nova_calls": 5, "alerts_sent": alerts_sent,
            "neighbors_notified": neighbor_count, "deterrent_fired": deterrent_fired,
            "similar_incidents": similar, "report_preview": report[:200],
            "has_voice": bool(voice_b64), "voice_model": voice_model,
            "sonic_attempted": sonic_attempted,
            "nova_act_report": act_report.get("portal") if act_report else None
        })

    except Exception as e:
        sse("error", f"Pipeline error: {str(e)}", {"traceback": traceback.format_exc()})
    finally:
        db.close()


def _notify_authorities_ntfy(region, nova_result, incident_id):
    import httpx
    try:
        httpx.post(f"https://ntfy.sh/paws-authorities-{region}",
            data=f"🚨 PAWS: {nova_result.get('animal','Unknown')} | "
                 f"Sev {nova_result.get('severity',0)}/10 | "
                 f"Behavior: {nova_result.get('behavior','unknown')} | "
                 f"Incident #{incident_id}",
            headers={"Title": f"Wildlife Alert — {region.upper()}",
                     "Priority": "urgent", "Tags": "rotating_light"},
            timeout=10)
        return True
    except:
        return False


def handle_farmer_feedback(incident_id: int, feedback: str):
    from agents.dataset_agent import update_frame_metadata
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return False
        incident.human_verified = True
        incident.human_feedback = feedback  # "confirmed" or "false_positive"
        db.commit()
        label = "confirmed_threat_human_verified" if feedback == "confirmed" else "false_positive_human_verified"
        update_frame_metadata(incident.animal, incident.created_at, label)
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()
