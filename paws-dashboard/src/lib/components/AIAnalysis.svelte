<script lang="ts">
  import { getVoiceAlert } from '$lib/api';
  
  export let threat: any = null;
  
  let loading = false;
  let playingVoice = false;

  function sevColor(severity: number) {
    if (severity >= 8) return 'var(--red)';
    if (severity >= 6) return 'var(--amber)';
    if (severity >= 4) return '#f59e0b';
    return 'var(--green)';
  }

  async function playVoiceAlert() {
    if (!threat || playingVoice) return;
    try {
      playingVoice = true;
      const data = await getVoiceAlert(threat.id);
      const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
      audio.onended = () => { playingVoice = false; };
      await audio.play();
    } catch (e) {
      console.error('Voice playback failed', e);
      playingVoice = false;
    }
  }
</script>

<div class="ai-panel">
  <div class="ai-header">
    <span class="ai-icon">🤖</span>
    <span class="ai-label">AI Analysis</span>
    <span class="ai-model">Nova 2 Lite</span>
  </div>
  
  {#if loading}
    <div class="ai-thinking">
      <div class="thinking-dot"></div>
      <span>AI analyzing threat...</span>
    </div>
  {:else if threat}
    <div class="ai-assessment space-y-3">
      <!-- What it's doing -->
      {#if threat.behavior_description}
        <div class="ai-behavior">
          <span class="behavior-label text-xs font-semibold" style="color: var(--text-secondary);">What it's doing:</span>
          <p class="behavior-text text-sm mt-1" style="color: var(--text-primary);">
            {threat.behavior_description}
          </p>
        </div>
      {/if}
      
      <!-- Threat level bar -->
      <div class="ai-severity-bar">
        <span style="color: var(--text-secondary);">Threat level</span>
        <div class="sev-track">
          <div 
            class="sev-fill" 
            style="width: {(threat.severity || 0) * 10}%; background: {sevColor(threat.severity || 0)}"
          ></div>
        </div>
        <span class="sev-num">{threat.severity || 0}/10</span>
      </div>
      
      <!-- AI Reasoning -->
      {#if threat.reasoning}
        <div class="ai-recommendation p-2 rounded" style="background: var(--blue-bg); color: var(--blue); font-size: 13px;">
          💡 {threat.reasoning}
        </div>
      {/if}
      
      <!-- Nova Report -->
      {#if threat.report}
        <div class="ai-report text-sm leading-relaxed" style="color: var(--text-secondary);">
          {threat.report}
        </div>
      {/if}
      
      <!-- Similar past incidents -->
      {#if threat.similar_incidents?.length}
        <div class="ai-similar text-xs" style="color: var(--text-muted);">
          <span class="similar-label font-semibold">Similar past incident:</span>
          <span class="ml-1">
            #{threat.similar_incidents[0].id} — 
            {threat.similar_incidents[0].animal}, 
            severity {threat.similar_incidents[0].severity}
            ({(threat.similar_incidents[0].similarity * 100).toFixed(0)}% match)
          </span>
        </div>
      {/if}
    </div>
    
    <!-- Voice alert playback -->
    {#if threat.has_voice_alert}
      <button class="voice-btn" on:click={playVoiceAlert} disabled={playingVoice}>
        {playingVoice ? '🔊 Playing...' : '▶ Hear alert'}
      </button>
    {/if}
  {:else}
    <div class="text-sm text-center py-4" style="color: var(--text-muted);">
      No active threat to analyze
    </div>
  {/if}
</div>
