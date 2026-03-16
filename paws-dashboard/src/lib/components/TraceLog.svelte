<script lang="ts">
  export let events = [];

  const STEP_LABELS = {
    stream_start: 'Stream Starting',
    stream_connecting: 'Connecting to Modal',
    stream_active: 'Stream Active',
    stream_ended: 'Stream Ended',
    yolo: 'YOLO Detection',
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
    complete: 'Pipeline complete',
    error: 'Error'
  };
  
  // Determine if a step is "in progress" (starts with emoji but no checkmark/X)
  function isInProgress(message: string): boolean {
    return message && !message.includes('✅') && !message.includes('❌') && !message.includes('⏭️');
  }
</script>

<div class="bg-gray-950 p-4 rounded-lg shadow-lg border border-gray-800 h-96 flex flex-col font-mono text-xs">
  <h2 class="text-green-500 font-bold mb-3 border-b border-gray-800 pb-2 uppercase tracking-wider">Live Pipeline Trace</h2>
  <div class="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
    {#each events.slice().reverse() as event (event.timestamp + event.step)}
      <div class="flex items-start gap-3 p-2 rounded {event.step === 'complete' ? 'bg-green-900/30' : event.step === 'error' ? 'bg-red-900/30' : 'bg-gray-900/50 hover:bg-gray-800/80 transition-colors'}">
        <div class="w-16 shrink-0 text-gray-500 tabular-nums">+{event.elapsed_ms}ms</div>
        <div class="flex-1 min-w-0 flex items-start gap-2">
          {#if isInProgress(event.message)}
            <div class="spinner mt-0.5"></div>
          {/if}
          <div class="flex-1">
            <div class="font-bold {event.step === 'complete' ? 'text-green-400' : event.step === 'error' ? 'text-red-400' : 'text-blue-400'}">
              {STEP_LABELS[event.step] || event.step}
            </div>
            <div class="text-gray-300 break-words">{event.message}</div>
          </div>
        </div>
      </div>
    {/each}
    {#if events.length === 0}
      <div class="text-gray-600 text-center italic mt-10">Waiting for detections...</div>
    {/if}
  </div>
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: #374151;
    border-radius: 3px;
  }
  
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid #374151;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
