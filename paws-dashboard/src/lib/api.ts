export const API_BASE = 'http://localhost:8000';

export type Incident = {
  id: number;
  animal: string;
  confidence: number;
  region: string;
  status: string;
  severity: number | null;
  behavior: string | null;
  behavior_description: string | null;
  animal_count: number | null;
  reasoning: string | null;
  report: string | null;
  deterrent_type: string | null;
  similar_incidents: SimilarIncident[];
  alerts_sent: Record<string, string>;
  neighbors_notified: number;
  has_voice_alert: boolean;
  voice_model: string | null;
  sonic_attempted: boolean | null;
  nova_act_report: string | null;
  advisories: string | null;
  human_verified: boolean;
  human_feedback: string | null;
  pipeline_ms: number | null;
  source_model: string;
  camera_id: string;
  created_at: string | null;
};

export type SimilarIncident = {
  id: number;
  animal: string;
  severity: number;
  similarity: number;
};

export type Stats = {
  total_detections: number;
  threats_confirmed: number;
  threats_dismissed: number;
  avg_pipeline_ms: number;
  nova_api_calls: number;
  farms_in_mesh: number;
  uptime_seconds: number;
  services: Record<string, string>;
};

export type SSEEvent = {
  pipeline_id: string;
  step: string;
  message: string;
  data: Record<string, unknown>;
  elapsed_ms: number;
  timestamp: string;
};

export async function fetchIncidents(limit = 50): Promise<Incident[]> {
  const res = await fetch(`${API_BASE}/api/incidents?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch incidents');
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

export async function simulate(scenario: string): Promise<void> {
  await fetch(`${API_BASE}/api/simulate/${scenario}`, { method: 'POST' });
}

export async function getVoiceAlert(incidentId: number): Promise<{ audio_b64: string; text: string }> {
  const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/voice`);
  if (!res.ok) throw new Error('Voice generation failed');
  return res.json();
}

export async function sendFeedback(incidentId: number, feedback: 'confirmed' | 'false_positive'): Promise<void> {
  await fetch(`${API_BASE}/api/feedback/${incidentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback })
  });
}

export function createSSEConnection(onEvent: (e: SSEEvent) => void): EventSource {
  const es = new EventSource(`${API_BASE}/api/sse`);
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.step !== 'heartbeat') onEvent(data as SSEEvent);
    } catch {
      // ignore malformed
    }
  };
  return es;
}
