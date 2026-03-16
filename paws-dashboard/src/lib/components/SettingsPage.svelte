<script>
  const config = {
    farm_designation: {
      lat: 23.32,
      lon: 62.32
    },
    user_email: 'user-conf/etc',
    last_recent_limit_hr: 12
  };
  
  const remotes = [
    { name: 'Baboon Troop', dist: '0.2mi conf/st+', status: 'online' },
    { name: 'Horker Elephant Park', dist: '0.1mi conf/st+', status: 'online' },
    { name: 'Brooks East Star Cam', dist: '0.5mi conf/st+', status: 'online' },
    { name: 'Wolf Sanctuary Cam', dist: '0.7mi conf/st+', status: 'offline' },
    { name: 'IP Camera — North Track', dist: '0.0mi conf/st+', status: 'offline' }
  ];
  
  const systems = [
    { name: 'YOLO-World', health: 'normal', model: 'model-01', runtime: 'inference v5' },
    { name: 'Nova 2 Lite', health: 'normal', model: 'bedrock v3', runtime: '' },
    { name: 'Nova Embeds', health: 'normal', model: 'embed-bedrock-v3', runtime: 'Similarity matrix M×K=f1' },
    { name: 'ntfy.sh', health: 'nominal', model: '', runtime: 'Restartable on publish' },
    { name: 'Edge (Hawtly)', health: 'not configured', model: '', runtime: 'Bus not registered' }
  ];
</script>

<div class="settings-page">
  <div class="page-header">
    <h2>Settings</h2>
  </div>
  
  <!-- Farm Designation -->
  <div class="section-card">
    <h3>Farm Designation</h3>
    <div class="config-grid">
      <div class="config-row">
        <span class="config-label">Lat:</span>
        <span class="config-value">{config.farm_designation.lat}</span>
      </div>
      <div class="config-row">
        <span class="config-label">Lon:</span>
        <span class="config-value">{config.farm_designation.lon}</span>
      </div>
      <div class="config-row full-width">
        <span class="config-label">User email (conf/etc):</span>
        <input type="text" value={config.user_email} class="config-input"/>
      </div>
      <div class="config-row full-width">
        <span class="config-label">Last recent limit (hr):</span>
        <input type="number" value={config.last_recent_limit_hr} class="config-input"/>
      </div>
    </div>
    <button class="btn-save">Save Configuration</button>
  </div>
  
  <!-- Remote Management -->
  <div class="section-card">
    <div class="section-header">
      <h3>Remote Management</h3>
      <button class="btn-add">+ Add Stream</button>
    </div>
    
    <div class="remotes-list">
      {#each remotes as remote}
        <div class="remote-item">
          <div class="remote-info">
            <span class="remote-name">{remote.name}</span>
            <span class="remote-dist">{remote.dist}</span>
          </div>
          <div class="remote-actions">
            <span class="remote-status {remote.status}">{remote.status}</span>
            <button class="btn-icon">🗑️</button>
          </div>
        </div>
      {/each}
    </div>
  </div>
  
  <!-- System Status -->
  <div class="section-card">
    <h3>System Status</h3>
    
    <div class="systems-list">
      {#each systems as system}
        <div class="system-item">
          <div class="system-main">
            <div class="system-name">
              <span class="system-icon">
                {#if system.health === 'normal' || system.health === 'nominal'}
                  ✅
                {:else}
                  ⚠️
                {/if}
              </span>
              {system.name}
            </div>
            <div class="system-details">
              {#if system.model}
                <span class="detail-item">{system.model}</span>
              {/if}
              {#if system.runtime}
                <span class="detail-item">{system.runtime}</span>
              {/if}
            </div>
          </div>
          <div class="system-health {system.health.replace(' ', '-')}">{system.health}</div>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .settings-page {
    padding: 1rem;
    max-width: 1000px;
    margin: 0 auto;
  }
  
  .page-header {
    margin-bottom: 1.5rem;
  }
  
  .page-header h2 {
    font-size: 1.5rem;
    font-weight: 700;
  }
  
  .section-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin-bottom: 1rem;
  }
  
  .section-card h3 {
    font-size: 1.125rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }
  
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
  }
  
  .section-header h3 {
    margin-bottom: 0;
  }
  
  .config-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
  }
  
  @media (max-width: 768px) {
    .config-grid {
      grid-template-columns: 1fr;
    }
  }
  
  .config-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .config-row.full-width {
    grid-column: 1 / -1;
  }
  
  .config-label {
    font-size: 0.875rem;
    font-weight: 500;
    min-width: 150px;
  }
  
  .config-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    color: var(--text-secondary);
  }
  
  .config-input {
    flex: 1;
    padding: 0.5rem 0.75rem;
    background: var(--bg-page);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
  }
  
  .btn-save {
    padding: 0.75rem 1.5rem;
    background: var(--green);
    border: none;
    border-radius: 0.375rem;
    color: #fff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  .btn-save:hover {
    opacity: 0.9;
  }
  
  .btn-add {
    padding: 0.5rem 1rem;
    background: var(--blue);
    border: none;
    border-radius: 0.375rem;
    color: #fff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
  }
  
  .remotes-list, .systems-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .remote-item, .system-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem;
    background: var(--bg-elevated);
    border-radius: 0.375rem;
  }
  
  .remote-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .remote-name {
    font-size: 0.875rem;
    font-weight: 500;
  }
  
  .remote-dist {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
  
  .remote-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .remote-status {
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 600;
  }
  
  .remote-status.online {
    background: var(--green-bg);
    color: var(--green);
  }
  
  .remote-status.offline {
    background: var(--bg-border);
    color: var(--text-muted);
  }
  
  .btn-icon {
    width: 2rem;
    height: 2rem;
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 1rem;
    opacity: 0.6;
    transition: opacity 0.2s;
  }
  
  .btn-icon:hover {
    opacity: 1;
  }
  
  .system-main {
    flex: 1;
  }
  
  .system-name {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 0.25rem;
  }
  
  .system-icon {
    font-size: 1rem;
  }
  
  .system-details {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .detail-item {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  .system-health {
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
  }
  
  .system-health.normal,
  .system-health.nominal {
    background: var(--green-bg);
    color: var(--green);
  }
  
  .system-health.not-configured {
    background: var(--amber-bg);
    color: var(--amber);
  }
</style>
