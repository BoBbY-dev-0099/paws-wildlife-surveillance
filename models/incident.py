from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum

engine = create_engine("sqlite:///paws_v12.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class IncidentStatus(str, enum.Enum):
    ANALYZING = "analyzing"
    ALERTED = "alerted"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    animal = Column(String, nullable=False)
    confidence = Column(Float)
    camera_id = Column(String, default="default")
    region = Column(String)
    status = Column(String, default=IncidentStatus.ANALYZING)
    source_model = Column(String, default="yolo-world")
    image_b64 = Column(Text)
    bbox = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Nova 2 Lite — analysis
    nova_threat_confirmed = Column(Boolean)
    nova_severity = Column(Integer)
    nova_behavior = Column(String)
    nova_animal = Column(String)
    nova_animal_count = Column(Integer)          # from Perplexity
    nova_behavior_description = Column(Text)     # from Perplexity
    nova_reasoning = Column(Text)
    nova_deterrent_type = Column(String)
    nova_raw_json = Column(Text)
    nova_report = Column(Text)                   # Narrative report from 3rd Nova call

    # Nova Embeddings
    embedding_dims = Column(Integer)
    similar_incidents = Column(Text)             # JSON list of similar past incidents

    # Voice alert
    has_voice_alert = Column(Boolean, default=False)
    
    # Nova Sonic tracking
    voice_model = Column(String, nullable=True, default=None)
    sonic_attempted = Column(Boolean, nullable=True, default=None)
    
    # Nova Act results
    nova_act_report = Column(Text, nullable=True, default=None)
    advisories = Column(Text, nullable=True, default=None)

    # Alerts
    alerts_sent = Column(Text)
    neighbors_notified = Column(Integer, default=0)
    authority_notified = Column(Boolean, default=False)
    deterrent_fired = Column(Boolean, default=False)

    # Human feedback (from Telegram inline buttons)
    human_verified = Column(Boolean, default=False)
    human_feedback = Column(String)

    # Performance
    pipeline_ms = Column(Integer)

Base.metadata.create_all(engine)
