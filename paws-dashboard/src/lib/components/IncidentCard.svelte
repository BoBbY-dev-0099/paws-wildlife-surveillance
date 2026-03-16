<script lang="ts">
  import { getVoiceAlert, sendFeedback } from '$lib/api';

  export let incident;
  
  let expanded = false;
  let playingAudio = false;
  let feedbackStatus = incident.human_feedback;
  let submittingFeedback = false;

  async function playVoiceAlert() {
    if (playingAudio) return;
    try {
      playingAudio = true;
      const data = await getVoiceAlert(incident.id);
      const audio = new Audio(`data:audio/mp3;base64,${data.audio_b64}`);
      audio.onended = () => { playingAudio = false; };
      await audio.play();
    } catch (e) {
      console.error(e);
      playingAudio = false;
      alert('Failed to play voice alert');
    }
  }

  async function handleFeedback(type) {
    if (feedbackStatus || submittingFeedback) return;
    try {
      submittingFeedback = true;
      await sendFeedback(incident.id, type);
      feedbackStatus = type;
    } catch (e) {
      alert('Failed to submit feedback');
    } finally {
      submittingFeedback = false;
    }
  }

  function formatDate(isoStr) {
    if (!isoStr) return 'Unknown time';
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
</script>

<div class="bg-gray-900 rounded-lg overflow-hidden border border-gray-800 hover:border-gray-700 transition-colors">
  <!-- Header row always visible -->
  <div class="p-4 flex items-center justify-between cursor-pointer" on:click={() => expanded = !expanded}>
    <div class="flex items-center gap-4">
      <div class="flex items-center justify-center w-10 h-10 rounded-full font-bold text-lg
        {incident.status === 'alerted' ? 'bg-red-900/50 text-red-500' : 'bg-gray-800 text-gray-400'}">
        {incident.severity || '-'}
      </div>
      <div>
        <h3 class="font-bold text-white uppercase tracking-wider flex items-center gap-2">
          {incident.animal} 
          <span class="text-xs font-mono font-normal text-gray-500">#{incident.id}</span>
          {#if incident.status === 'alerted'}
            <span class="px-2 py-0.5 rounded bg-red-900/50 text-red-400 text-xs font-mono">THREAT</span>
          {/if}
          {#if incident.status === 'dismissed'}
            <span class="px-2 py-0.5 rounded bg-gray-800 text-gray-400 text-xs font-mono">DISMISSED</span>
          {/if}
        </h3>
        <p class="text-sm text-gray-400 mt-0.5 font-mono">
          {formatDate(incident.created_at)} • {incident.region} • conf: {(incident.confidence * 100).toFixed(0)}%
        </p>
      </div>
    </div>
    
    <button class="text-gray-500 hover:text-white p-2">
      <svg class="w-5 h-5 transform transition-transform {expanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
    </button>
  </div>

  <!-- Expanded Details -->
  {#if expanded}
    <div class="p-4 border-t border-gray-800 bg-gray-950/50">
      
      <!-- Badges row -->
      <div class="flex flex-wrap gap-2 mb-4">
        {#if incident.behavior}
          <span class="px-2 py-1 bg-blue-900/30 text-blue-400 text-xs font-mono rounded border border-blue-900/50">
            Behavior: {incident.behavior}
          </span>
        {/if}
        {#if incident.deterrent_type && incident.deterrent_type !== 'none'}
          <span class="px-2 py-1 bg-yellow-900/30 text-yellow-400 text-xs font-mono rounded border border-yellow-900/50">
            Deterrent: {incident.deterrent_type} {incident.deterrent_fired ? '(Fired)' : ''}
          </span>
        {/if}
        {#if Object.keys(incident.alerts_sent || {}).length > 0}
          <span class="px-2 py-1 bg-purple-900/30 text-purple-400 text-xs font-mono rounded border border-purple-900/50">
            Alerts Dispatch: Ok
          </span>
        {/if}
        {#if incident.neighbors_notified > 0}
          <span class="px-2 py-1 bg-emerald-900/30 text-emerald-400 text-xs font-mono rounded border border-emerald-900/50">
            Mesh: {incident.neighbors_notified} farms
          </span>
        {/if}
      </div>

      <!-- Nova Behavior Description -->
      {#if incident.behavior_description}
        <div class="mb-4">
          <div class="font-mono text-xs text-gray-500 mb-1">Nova Vision Analysis</div>
          <p class="text-sm text-gray-300 bg-gray-900 p-2 rounded border border-gray-800">
            {incident.behavior_description}
          </p>
        </div>
      {/if}

      <!-- Interactive Buttons -->
      <div class="flex items-center gap-3 mb-4">
        {#if incident.has_voice_alert}
          <button
             on:click|stopPropagation={playVoiceAlert}
             disabled={playingAudio}
             class="flex items-center gap-2 px-3 py-1.5 rounded border border-amber-500/30 text-amber-500 font-mono text-xs hover:bg-amber-500/10 transition-colors disabled:opacity-50"
          >
            {#if playingAudio}
              <span class="animate-pulse">🔊 Playing...</span>
            {:else}
              ▶ Play Voice Alert
            {/if}
          </button>
        {/if}

        <div class="flex items-center gap-2 ml-auto">
           {#if feedbackStatus}
              <span class="text-xs font-mono px-2 py-1 rounded {feedbackStatus === 'confirmed' ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'}">
                {feedbackStatus === 'confirmed' ? '✅ Verified Threat' : '❌ Verified False Positive'}
              </span>
           {:else}
              <button disabled={submittingFeedback} on:click|stopPropagation={() => handleFeedback('confirmed')} class="text-xs font-mono px-2 py-1 bg-gray-800 hover:bg-green-900/50 text-gray-300 hover:text-green-400 border border-transparent hover:border-green-900/50 rounded transition-colors disabled:opacity-50">✅ Confirm</button>
              <button disabled={submittingFeedback} on:click|stopPropagation={() => handleFeedback('false_positive')} class="text-xs font-mono px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white border border-transparent hover:border-gray-600 rounded transition-colors disabled:opacity-50">❌ False Positive</button>
           {/if}
        </div>
      </div>

      <!-- B2: Similar Incidents (Nova Embed) -->
      {#if incident.similar_incidents?.length > 0}
        <div class="mt-4 mb-4">
          <div class="font-mono text-[10px] text-teal-500 mb-2 uppercase tracking-wide">Nova Embeddings — Similar Past Incidents</div>
          <div class="space-y-1">
            {#each incident.similar_incidents as sim}
              <div class="flex items-center gap-3 py-1 border-b border-gray-800/50 font-mono text-[11px]">
                <span class="text-gray-500">#{sim.id}</span>
                <span class="text-gray-300">{sim.animal}</span>
                <span class="text-orange-400">sev {sim.severity}</span>
                <span class="ml-auto text-teal-400">{(sim.similarity * 100).toFixed(1)}% match</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- B3: Nova Report -->
      {#if incident.report}
        <div class="mt-4 bg-gray-900 border border-gray-800 rounded p-3">
          <div class="font-mono text-[10px] text-blue-400 mb-2 uppercase tracking-wide flex items-center gap-2">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            Nova 2 Lite — Auto-Generated Report
          </div>
          <p class="font-sans text-sm text-gray-300 leading-relaxed">
            {incident.report}
          </p>
        </div>
      {/if}
      
    </div>
  {/if}
</div>
