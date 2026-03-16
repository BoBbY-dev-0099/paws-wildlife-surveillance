<script>
  import { onMount } from 'svelte';
  import { AlertTriangle, CheckCircle, XCircle } from 'lucide-svelte';
  import { API_BASE_URL } from '$lib/config';
  
  let incidents = [];
  let filterStatus = 'all';
  let loading = true;
  
  async function fetchIncidents() {
    loading = true;
    try {
      const res = await fetch('${API_BASE_URL}/api/incidents');
      if (res.ok) {
        incidents = await res.json();
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    } finally {
      loading = false;
    }
  }
  
  function timeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }
  
  $: filteredIncidents = filterStatus === 'all' 
    ? incidents 
    : incidents.filter(i => {
        if (filterStatus === 'alerted') return i.severity_score >= 6;
        if (filterStatus === 'dismissed') return i.severity_score < 6;
        return true;
      });
  
  onMount(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 30000);
    return () => clearInterval(interval);
  });
</script>

<div class="incidents-page">
  <!-- Filter Tabs -->
  <div class="filter-tabs">
    <button 
      class="filter-tab {filterStatus === 'all' ? 'active' : ''}"
      on:click={() => filterStatus = 'all'}
    >
      All Status ({incidents.length})
    </button>
    <button 
      class="filter-tab {filterStatus === 'alerted' ? 'active' : ''}"
      on:click={() => filterStatus = 'alerted'}
    >
      <AlertTriangle size={14} />
      Alerted
    </button>
    <button 
      class="filter-tab {filterStatus === 'dismissed' ? 'active' : ''}"
      on:click={() => filterStatus = 'dismissed'}
    >
      <CheckCircle size={14} />
      Low Severity
    </button>
  </div>
  
  <!-- Incidents List -->
  {#if loading}
    <div class="loading">Loading incidents...</div>
  {:else if filteredIncidents.length === 0}
    <div class="empty-state">
      <AlertTriangle size={48} />
      <p>No incidents found</p>
    </div>
  {:else}
    <div class="incidents-list">
      {#each filteredIncidents as incident}
        <div class="incident-card">
          <div class="incident-header">
            <div class="incident-icon severity-{incident.severity_score}">
              {#if incident.severity_score >= 7}
                <AlertTriangle size={20} />
              {:else}
                <CheckCircle size={20} />
              {/if}
            </div>
            
            <div class="incident-main">
              <div class="incident-title">
                <strong>{incident.animal.toUpperCase()}</strong> 
                {incident.behavior} · conf {Math.round(incident.confidence * 100)}%
              </div>
              <div class="incident-meta">
                {incident.location} · {timeAgo(incident.timestamp)}
              </div>
            </div>
            
            <div class="incident-badges">
              {#if incident.severity_score >= 6}
                <span class="status-badge alerted">ALERTED</span>
              {:else}
                <span class="status-badge low">LOW</span>
              {/if}
              
              {#if incident.feedback_label}
                <span class="feedback-badge verified">
                  <CheckCircle size={12} />
                  VERIFIED
                </span>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .incidents-page {
    padding: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .filter-tabs {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  
  .filter-tab {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1rem;
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .filter-tab:hover {
    color: var(--text-primary);
  }
  
  .filter-tab.active {
    background: var(--green);
    border-color: var(--green);
    color: #fff;
  }
  
  .loading,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
  }
  
  .empty-state {
    gap: 1rem;
  }
  
  .incidents-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .incident-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    overflow: hidden;
    transition: all 0.2s;
  }
  
  .incident-card:hover {
    border-color: var(--green);
  }
  
  .incident-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem;
  }
  
  .incident-icon {
    width: 3rem;
    height: 3rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  
  .incident-icon[class*="severity-1"],
  .incident-icon[class*="severity-2"],
  .incident-icon[class*="severity-3"] {
    background: var(--green-bg);
    color: var(--green);
  }
  
  .incident-icon[class*="severity-4"],
  .incident-icon[class*="severity-5"],
  .incident-icon[class*="severity-6"] {
    background: var(--amber-bg);
    color: var(--amber);
  }
  
  .incident-icon[class*="severity-7"],
  .incident-icon[class*="severity-8"],
  .incident-icon[class*="severity-9"],
  .incident-icon[class*="severity-10"] {
    background: var(--red-bg);
    color: var(--red);
  }
  
  .incident-main {
    flex: 1;
    min-width: 0;
  }
  
  .incident-title {
    font-size: 0.9375rem;
    margin-bottom: 0.375rem;
  }
  
  .incident-meta {
    font-size: 0.8125rem;
    color: var(--text-muted);
  }
  
  .incident-badges {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
    flex-wrap: wrap;
  }
  
  .status-badge {
    padding: 0.375rem 0.75rem;
    border-radius: 0.375rem;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
    font-weight: 600;
  }
  
  .status-badge.alerted {
    background: var(--red-bg);
    color: var(--red);
  }
  
  .status-badge.low {
    background: var(--bg-elevated);
    color: var(--text-muted);
  }
  
  .feedback-badge {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: var(--green-bg);
    color: var(--green);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    font-weight: 600;
  }
</style>
