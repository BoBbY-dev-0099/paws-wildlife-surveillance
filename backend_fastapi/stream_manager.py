"""
Stream Management Module for PAWS
Manages camera streams/sources dynamically
"""
import json
from pathlib import Path
from typing import List, Dict, Any

STREAMS_FILE = Path(__file__).parent / "streams.json"

def load_streams() -> List[Dict[str, Any]]:
    """Load streams from JSON file"""
    if not STREAMS_FILE.exists():
        # Default streams
        default_streams = [
            {"id": "cam1", "name": "North Perimeter", "url": "camera:0", "type": "RTSP", "active": True},
            {"id": "cam2", "name": "South Gate", "url": "", "type": "HLS", "active": False},
            {"id": "cam3", "name": "East Fence", "url": "", "type": "RTSP", "active": False},
            {"id": "cam4", "name": "West Field", "url": "", "type": "HLS", "active": False}
        ]
        save_streams(default_streams)
        return default_streams
    
    with open(STREAMS_FILE, 'r') as f:
        return json.load(f)

def save_streams(streams: List[Dict[str, Any]]):
    """Save streams to JSON file"""
    with open(STREAMS_FILE, 'w') as f:
        json.dump(streams, f, indent=2)

def get_stream_by_id(stream_id: str) -> Dict[str, Any] | None:
    """Get a specific stream by ID"""
    streams = load_streams()
    return next((s for s in streams if s['id'] == stream_id), None)

def add_stream(name: str, url: str, stream_type: str) -> Dict[str, Any]:
    """Add a new stream"""
    streams = load_streams()
    
    # Generate new ID
    max_id = 0
    for s in streams:
        if s['id'].startswith('cam'):
            try:
                num = int(s['id'][3:])
                max_id = max(max_id, num)
            except ValueError:
                pass
    
    new_stream = {
        "id": f"cam{max_id + 1}",
        "name": name,
        "url": url,
        "type": stream_type,
        "active": True
    }
    
    streams.append(new_stream)
    save_streams(streams)
    return new_stream

def update_stream(stream_id: str, name: str | None = None, url: str | None = None, 
                  stream_type: str | None = None, active: bool | None = None) -> Dict[str, Any] | None:
    """Update an existing stream"""
    streams = load_streams()
    stream = next((s for s in streams if s['id'] == stream_id), None)
    
    if not stream:
        return None
    
    if name is not None:
        stream['name'] = name
    if url is not None:
        stream['url'] = url
    if stream_type is not None:
        stream['type'] = stream_type
    if active is not None:
        stream['active'] = active
    
    save_streams(streams)
    return stream

def delete_stream(stream_id: str) -> bool:
    """Delete a stream"""
    streams = load_streams()
    original_len = len(streams)
    streams = [s for s in streams if s['id'] != stream_id]
    
    if len(streams) < original_len:
        save_streams(streams)
        return True
    return False
