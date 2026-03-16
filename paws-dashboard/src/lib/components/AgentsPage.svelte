<script>
  let selectedAgent = 'radiant_charge';
  
  const agents = [
    { id: 'radiant_charge', label: '⚡ Radiant Charge' },
    { id: 'void_pack', label: '🌑 Void Pack' },
    { id: 'nova_embodiment', label: '🧠 Nova Embodiment' },
    { id: 'grey_01', label: '🤖 Grey 01 (pre-rec)' }
  ];
  
  const events = [
    { id: 'radiant_charge', label: '💥 Radiant Charge' },
    { id: 'void_pack', label: '🌑 Void Pack' },
    { id: 'approaching', label: '🚶 Approaching' },
    { id: 'low_severity', label: '🟢 Low Severity' }
  ];
</script>

<div class="agents-page">
  <div class="page-header">
    <h2>Strands Agent Trace</h2>
    <p class="subtitle">Watch Strands Nova models coordinate in real time</p>
  </div>
  
  <!-- Agent Tabs -->
  <div class="agent-tabs">
    {#each agents as agent}
      <button 
        class="agent-tab {selectedAgent === agent.id ? 'active' : ''}"
        on:click={() => selectedAgent = agent.id}
      >
        {agent.label}
      </button>
    {/each}
  </div>
  
  <!-- Events Bar -->
  <div class="events-bar">
    {#each events as event}
      <span class="event-badge">{event.label}</span>
    {/each}
  </div>
  
  <!-- Trace Viewer (Empty State) -->
  <div class="trace-viewer">
    <div class="empty-state">
      <div class="empty-icon">🔍</div>
      <p class="empty-text">No active agent traces</p>
      <p class="empty-hint">Agents will appear here when a detection occurs</p>
    </div>
  </div>
</div>

<style>
  .agents-page {
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .page-header {
    margin-bottom: 1.5rem;
  }
  
  .page-header h2 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  
  .subtitle {
    color: var(--text-muted);
    font-size: 0.875rem;
  }
  
  .agent-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  
  .agent-tab {
    padding: 0.5rem 1rem;
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .agent-tab:hover {
    color: var(--text-primary);
  }
  
  .agent-tab.active {
    background: var(--blue);
    border-color: var(--blue);
    color: #fff;
  }
  
  .events-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  
  .event-badge {
    padding: 0.375rem 0.75rem;
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  .trace-viewer {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .empty-state {
    text-align: center;
    padding: 3rem;
  }
  
  .empty-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
  }
  
  .empty-text {
    font-size: 1.125rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }
  
  .empty-hint {
    color: var(--text-muted);
    font-size: 0.875rem;
  }
</style>
