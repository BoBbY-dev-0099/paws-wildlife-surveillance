<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { API_BASE_URL } from '$lib/config';
  import DashboardLayout from '$lib/components/DashboardLayout.svelte';
  import LiveFeedPage from '$lib/components/LiveFeedPage.svelte';
  import IncidentsPage from '$lib/components/IncidentsPage.svelte';
  import MeshPage from '$lib/components/MeshPage.svelte';
  import DatasetPage from '$lib/components/DatasetPage.svelte';
  import AgentsPage from '$lib/components/AgentsPage.svelte';
  import SettingsPage from '$lib/components/SettingsPage.svelte';
  
  let currentTab = 'live';
  let theme = 'dark';
  let incidentCount = 0;
  
  async function fetchIncidentCount() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/incidents`);
      if (res.ok) {
        const data = await res.json();
        incidentCount = data.length;
      }
    } catch (err) {
      console.error('Failed to fetch incident count:', err);
    }
  }
  
  function setTheme(newTheme: string) {
    theme = newTheme;
    if (browser) {
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('paws-theme', newTheme);
    }
  }
  
  onMount(() => {
    const saved = localStorage.getItem('paws-theme') || 'dark';
    setTheme(saved);
    
    fetchIncidentCount();
    const interval = setInterval(fetchIncidentCount, 30000); // Update every 30s
    
    return () => clearInterval(interval);
  });
</script>

<svelte:head>
  <title>PAWS Dashboard — Live Monitoring</title>
</svelte:head>

<div class="dashboard">
  <DashboardLayout bind:currentTab bind:theme {incidentCount}>
    <!-- Content based on current tab -->
    {#if currentTab === 'live'}
      <LiveFeedPage />
    {:else if currentTab === 'incidents'}
      <IncidentsPage />
    {:else if currentTab === 'mesh'}
      <MeshPage />
    {:else if currentTab === 'dataset'}
      <DatasetPage />
    {:else if currentTab === 'agents'}
      <AgentsPage />
    {:else if currentTab === 'settings'}
      <SettingsPage />
    {/if}
  </DashboardLayout>
  
  <!-- Bottom Status Bar -->
  <div class="bottom-bar">
    <div class="bottom-content">
      <div class="services">
        <span class="service active">● YOLO-World</span>
        <span class="service active">● Nova Lite</span>
        <span class="service active">● ntfy.sh</span>
        <span class="service active">● Telegram</span>
        <span class="service inactive">● Edge</span>
      </div>
      <div class="stats">
        <span>Total: 4</span>
        <span>Avg: 2305ms</span>
        <span>Nova: 12</span>
        <span>Mesh: 4</span>
        <span>Up: 4h 24m</span>
      </div>
    </div>
  </div>
</div>

<style>
  .dashboard {
    min-height: 100vh;
    background: var(--bg-page);
    color: var(--text-primary);
    display: flex;
    flex-direction: column;
  }
  
  .bottom-bar {
    position: sticky;
    bottom: 0;
    background: var(--bg-card);
    border-top: 1px solid var(--bg-border);
    padding: 0.5rem 1rem;
    font-size: 0.75rem;
    z-index: 10;
  }
  
  .bottom-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .services {
    display: flex;
    gap: 1rem;
    color: var(--text-muted);
  }
  
  .service {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }
  
  .service.active {
    color: var(--green);
  }
  
  .service.inactive {
    color: var(--text-muted);
  }
  
  .stats {
    display: flex;
    gap: 1rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
</style>
