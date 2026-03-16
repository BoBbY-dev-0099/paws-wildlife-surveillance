<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { Radio, AlertTriangle, Map, Database, Bot, Settings, Sun, Moon, Sprout } from 'lucide-svelte';
  
  export let currentTab = 'live';
  export let theme = 'dark';
  export let incidentCount = 4;
  
  let simulateMenuOpen = false;
  
  const tabs = [
    { id: 'live', label: 'Live Feed', icon: Radio },
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle, badge: incidentCount },
    { id: 'mesh', label: 'Community Mesh', icon: Map },
    { id: 'dataset', label: 'Dataset', icon: Database },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];
  
  const verifiedServices = [
    { id: 'nova_lite', label: 'nova lite', active: true },
    { id: 'embeddings', label: 'embeddings', active: true },
    { id: 'sonic', label: 'sonic', active: false },
    { id: 'nova_act', label: 'nova act', active: false },
    { id: 'mesh', label: 'mesh', active: false }
  ];
  
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
  });
</script>

<!-- Top Navigation -->
<div class="top-nav">
  <div class="top-nav-main">
    <div class="brand">
      <span class="brand-icon">🐾</span>
      <span class="brand-text">PAWS</span>
    </div>
    
    <div class="farm-select">
      <button class="farm-btn">
        Baboon Troop <span class="dropdown-arrow">▾</span>
      </button>
    </div>
    
    <button class="btn-start">
      ▶ Start Engine
    </button>
    
    <div class="status-banner status-threat">
      🔴 ACTIVE THREAT
    </div>
    
    <div class="top-actions">
      <!-- Simulate dropdown -->
      <div class="simulate-dropdown-container">
        <button class="btn-secondary" on:click={() => simulateMenuOpen = !simulateMenuOpen}>
          Simulate <span class="dropdown-arrow">▾</span>
        </button>
      </div>
      
      <!-- Theme Switcher -->
      <div class="theme-switcher">
        <button 
          class="theme-btn {theme === 'dark' ? 'active' : ''}"
          on:click={() => setTheme('dark')}
          title="Dark"
        >
          <Moon size={16} />
        </button>
        <button 
          class="theme-btn {theme === 'light' ? 'active' : ''}"
          on:click={() => setTheme('light')}
          title="Light"
        >
          <Sun size={16} />
        </button>
        <button 
          class="theme-btn {theme === 'green' ? 'active' : ''}"
          on:click={() => setTheme('green')}
          title="Green"
        >
          <Sprout size={16} />
        </button>
      </div>
      
      <button class="btn-icon">
        <Settings size={16} />
      </button>
    </div>
  </div>
  
  
  <!-- Tab Navigation -->
  <div class="tab-nav">
    {#each tabs as tab}
      <button 
        class="tab-btn {currentTab === tab.id ? 'active' : ''}"
        on:click={() => currentTab = tab.id}
      >
        <svelte:component this={tab.icon} size={16} class="tab-icon" />
        <span class="tab-label">{tab.label}</span>
        {#if tab.badge}
          <span class="tab-badge">{tab.badge}</span>
        {/if}
      </button>
    {/each}
  </div>
</div>

<!-- Content Slot -->
<slot />

<style>
  .top-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--bg-card);
    border-bottom: 1px solid var(--bg-border);
  }
  
  .top-nav-main {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--bg-border);
  }
  
  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    font-size: 1.125rem;
  }
  
  .farm-select {
    position: relative;
  }
  
  .farm-btn {
    padding: 0.375rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .dropdown-arrow {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  .btn-start {
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-start:hover {
    background: var(--bg-elevated);
  }
  
  .status-banner {
    margin-left: auto;
    padding: 0.5rem 1.5rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  .status-threat {
    background: var(--red-bg);
    color: var(--red);
    animation: pulse-threat 2s ease-in-out infinite;
  }
  
  @keyframes pulse-threat {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }
  
  
  .top-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .btn-secondary {
    padding: 0.5rem 0.75rem;
    background: transparent;
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .theme-switcher {
    display: flex;
    gap: 0.25rem;
  }
  
  .theme-btn {
    width: 2rem;
    height: 2rem;
    border-radius: 0.25rem;
    border: 1px solid var(--bg-border);
    background: transparent;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .theme-btn.active {
    border-color: var(--blue);
    background: var(--blue-bg);
  }
  
  .btn-icon {
    width: 2rem;
    height: 2rem;
    border-radius: 0.25rem;
    border: 1px solid var(--bg-border);
    background: transparent;
    cursor: pointer;
  }
  
  /* Tab Navigation */
  .tab-nav {
    display: flex;
    gap: 0.25rem;
    padding: 0 1rem;
    background: rgba(var(--bg-card-rgb), 0.3);
    overflow-x: auto;
  }
  
  .tab-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s;
  }
  
  .tab-btn:hover {
    color: var(--text-primary);
  }
  
  .tab-btn.active {
    color: var(--blue);
    border-bottom-color: var(--blue);
  }
  
  .tab-icon {
    font-size: 1rem;
  }
  
  .tab-badge {
    background: var(--red);
    color: #fff;
    font-size: 0.75rem;
    padding: 0.125rem 0.375rem;
    border-radius: 9999px;
    font-weight: 600;
  }
</style>
