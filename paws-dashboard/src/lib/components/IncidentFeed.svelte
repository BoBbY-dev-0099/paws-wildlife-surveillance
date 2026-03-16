<script lang="ts">
  import { slide } from 'svelte/transition';
  import { sendFeedback, getVoiceAlert } from '$lib/api';
  
  export let incidents = [];
  
  let expanded = null;
  let activeLang = 'en';

  function sevColor(severity) {
    if (severity >= 8) return 'var(--red)';
    if (severity >= 6) return 'var(--amber)';
    if (severity >= 4) return '#f59e0b';
    return 'var(--green)';
  }

  function timeAgo(timestamp) {
    if (!timestamp) return 'unknown';
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  }

  async function feedback(id, type) {
    try {
      await sendFeedback(id, type);
      // Refresh incidents
      location.reload();
    } catch (e) {
      console.error('Feedback failed', e);
    }
  }

  async function playVoice(id) {
    try {
      const data = await getVoiceAlert(id);
      const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
      await audio.play();
    } catch (e) {
      console.error('Voice playback failed', e);
    }
  }
</script>

<div class="space-y-3 max-h-[800px] overflow-y-auto pr-2">
  <h2 class="text-sm font-semibold mb-3" style="color: var(--text-secondary);">Recent Detections</h2>
  
  {#each incidents.slice(0, 20) as inc (inc.id)}
    <div 
      class="incident-card {inc.status} {(inc.severity || 0) >= 7 ? 'critical' : ''}"
      on:click={() => expanded = expanded === inc.id ? null : inc.id}
      on:keydown={(e) => e.key === 'Enter' && (expanded = expanded === inc.id ? null : inc.id)}
      role="button"
      tabindex="0"
    >
      <!-- One-line summary -->
      <div class="inc-header">
        <div class="inc-sev" style="background:{sevColor(inc.severity)}">
          {inc.severity ?? '–'}
        </div>
        <div class="inc-main flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="inc-animal">{inc.animal.toUpperCase()}</span>
            <span class="inc-behavior">{inc.nova_behavior ?? 'unknown'}</span>
          </div>
        </div>
        <div class="inc-meta flex flex-col items-end gap-1">
          <span class="inc-time">{timeAgo(inc.created_at)}</span>
          <span class="inc-status-badge {inc.status}">{inc.status}</span>
        </div>
      </div>
      
      <!-- Expanded detail (on click) -->
      {#if expanded === inc.id}
        <div class="inc-detail mt-3 pt-3 space-y-3" style="border-top: 1px solid var(--bg-border);" transition:slide>
          <!-- Behavior description -->
          {#if inc.behavior_description}
            <p class="text-xs leading-relaxed" style="color: var(--text-secondary);">
              {inc.behavior_description}
            </p>
          {/if}
          
          <!-- Reasoning -->
          {#if inc.reasoning}
            <p class="inc-reasoning text-xs p-2 rounded leading-relaxed" style="background: var(--bg-elevated); color: var(--text-secondary);">
              {inc.reasoning}
            </p>
          {/if}
          
          <!-- Report -->
          {#if inc.report}
            <p class="inc-report text-xs leading-relaxed" style="color: var(--text-muted);">
              {inc.report}
            </p>
          {/if}
          
          <!-- Feedback -->
          {#if !inc.human_feedback}
            <div class="inc-feedback flex gap-2 pt-2">
              <button 
                on:click|stopPropagation={() => feedback(inc.id, 'confirmed')}
                class="flex-1 text-xs py-2 rounded font-medium transition-all"
                style="background: var(--green-bg); color: var(--green); border: 1px solid var(--green-dim);"
              >
                ✅ Real threat
              </button>
              <button 
                on:click|stopPropagation={() => feedback(inc.id, 'false_positive')}
                class="flex-1 text-xs py-2 rounded font-medium transition-all"
                style="background: var(--bg-elevated); color: var(--text-secondary); border: 1px solid var(--bg-border);"
              >
                ❌ False alarm
              </button>
            </div>
          {:else}
            <div class="text-xs text-center py-2 rounded" style="background: var(--green-bg); color: var(--green);">
              {inc.human_feedback === 'confirmed' ? '✅ Verified as real threat' : '❌ Marked as false alarm'}
            </div>
          {/if}
          
          <!-- Voice playback -->
          {#if inc.has_voice_alert}
            <button 
              on:click|stopPropagation={() => playVoice(inc.id)}
              class="w-full text-xs py-2 rounded font-medium transition-all"
              style="background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue);"
            >
              ▶ Hear voice alert
            </button>
          {/if}
        </div>
      {/if}
    </div>
  {/each}
  
  {#if incidents.length === 0}
    <div class="text-center py-12 rounded-lg" style="border: 1px dashed var(--bg-border);">
      <p class="text-sm" style="color: var(--text-muted);">No incidents recorded</p>
      <p class="text-xs mt-2" style="color: var(--text-muted);">Trigger a simulation to test the system</p>
    </div>
  {/if}
</div>

<style>
  .space-y-3 > * + * {
    margin-top: 0.75rem;
  }
  
  .inc-detail {
    animation: expand 0.2s ease-out;
  }
  
  @keyframes expand {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
