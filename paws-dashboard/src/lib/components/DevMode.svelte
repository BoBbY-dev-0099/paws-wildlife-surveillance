<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { slide } from 'svelte/transition';
  
  export let sseEvents = [];
  export let stats = null;
  
  const dispatch = createEventDispatcher();
  
  const STEP_LABELS = {
    gate: 'Gate check',
    debounce: 'Debounce',
    db: 'DB write',
    nova_lite: 'Nova 2 Lite',
    embeddings: 'Nova Embeddings',
    decision: 'Threat decision',
    nova_report: 'Nova 2 Lite (report)',
    sonic: 'Nova Sonic (voice)',
    nova_act: 'Nova Act (automation)',
    dataset: 'Dataset save',
    alerts: 'ntfy + Telegram',
    mesh: 'Community mesh',
    deterrent: 'Deterrent',
    authority: 'Authority notify',
    complete: 'Pipeline complete'
  };
</script>

<div class="dev-panel" transition:slide>
  <div class="p-4 border-b flex items-center justify-between" style="border-color: var(--bg-border);">
    <h3 class="font-semibold text-sm">Developer Mode</h3>
    <button 
      on:click={() => dispatch('close')}
      class="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
      style="background: var(--bg-elevated); color: var(--text-secondary);"
    >
      ✕
    </button>
  </div>
  
  <!-- Stats -->
  {#if stats}
    <div class="p-4 border-b" style="border-color: var(--bg-border);">
      <div class="text-xs space-y-2 font-mono">
        <div class="flex justify-between">
          <span style="color: var(--text-secondary);">Total detections:</span>
          <span style="color: var(--text-primary);">{stats.total_detections}</span>
        </div>
        <div class="flex justify-between">
          <span style="color: var(--text-secondary);">Avg pipeline:</span>
          <span style="color: var(--text-primary);">{stats.avg_pipeline_ms}ms</span>
        </div>
        <div class="flex justify-between">
          <span style="color: var(--text-secondary);">Nova calls:</span>
          <span style="color: var(--text-primary);">{stats.nova_api_calls}</span>
        </div>
        <div class="flex justify-between">
          <span style="color: var(--text-secondary);">Uptime:</span>
          <span style="color: var(--text-primary);">{Math.floor(stats.uptime_seconds / 3600)}h {Math.floor((stats.uptime_seconds % 3600) / 60)}m</span>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- Live Pipeline Trace -->
  <div class="p-4">
    <h4 class="text-xs font-semibold mb-3" style="color: var(--text-secondary);">LIVE PIPELINE TRACE</h4>
    <div class="max-h-[400px] overflow-y-auto space-y-2 text-xs font-mono">
      {#each sseEvents.slice().reverse().slice(0, 50) as event (event.timestamp + event.step)}
        <div 
          class="flex items-start gap-2 p-2 rounded transition-colors"
          class:bg-green-500={event.step === 'complete'}
          class:bg-red-500={event.step === 'error'}
          style="background: {event.step === 'complete' ? 'var(--green-bg)' : event.step === 'error' ? 'var(--red-bg)' : 'var(--bg-elevated)'};"
        >
          <div class="w-16 shrink-0 tabular-nums" style="color: var(--text-muted);">
            +{event.elapsed_ms}ms
          </div>
          <div class="flex-1 min-w-0">
            <div 
              class="font-bold"
              style="color: {event.step === 'complete' ? 'var(--green)' : event.step === 'error' ? 'var(--red)' : 'var(--blue)'};"
            >
              {STEP_LABELS[event.step] || event.step}
            </div>
            <div class="truncate" style="color: var(--text-secondary);">
              {event.message}
            </div>
          </div>
        </div>
      {/each}
      
      {#if sseEvents.length === 0}
        <div class="text-center py-8" style="color: var(--text-muted);">
          Waiting for detections...
        </div>
      {/if}
    </div>
  </div>
</div>
