<script>
  const stats = {
    total_incidents: 24,
    manually_verified: 7,
    need_review: 2
  };
  
  const labelDistribution = [
    { label: 'ELEPHANT (grazing)', count: 7, percentage: 25, color: 'var(--green)' },
    { label: 'Last hazard (trunk up)', count: 5, percentage: 18, color: 'var(--amber)' },
    { label: 'False positive (human etc.', count: 2, percentage: 7, color: 'var(--red)' },
    { label: 'data truncated', count: 1, percentage: 4, color: 'var(--text-muted)' },
    { label: 'old file/out', count: 3, percentage: 11, color: 'var(--green)' },
    { label: 'unknown duplicate', count: 2, percentage: 7, color: 'var(--green)' }
  ];
  
  const animals = ['elephant 14', 'wolf 4', 'baboon 3', 'jaguar 1'];
</script>

<div class="dataset-page">
  <div class="page-header">
    <h2>🔥 Training Dataset Flywheel</h2>
    <p class="subtitle">Every detection in stored for fine-tuning</p>
  </div>
  
  <!-- Stats Cards -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-value">{stats.total_incidents}</div>
      <div class="stat-label">total incidents</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{stats.manually_verified}</div>
      <div class="stat-label">manually verified ?</div>
    </div>
    <div class="stat-card">
      <div class="stat-value need-review">{stats.need_review}</div>
      <div class="stat-label">need review in S3 bucket</div>
    </div>
  </div>
  
  <!-- Label Distribution -->
  <div class="section-card">
    <h3>Label Distribution</h3>
    <p class="section-subtitle">conf adjusted to match fine tuning</p>
    
    <div class="distribution-list">
      {#each labelDistribution as item}
        <div class="distribution-item">
          <div class="item-label">{item.label}</div>
          <div class="item-bar">
            <div class="bar-fill" style="width: {item.percentage}%; background: {item.color};"></div>
          </div>
          <div class="item-count">{item.count} ({item.percentage}%)</div>
        </div>
      {/each}
    </div>
  </div>
  
  <!-- By Animal -->
  <div class="section-card">
    <h3>By Animal</h3>
    <div class="animal-tags">
      {#each animals as animal}
        <span class="animal-tag">{animal}</span>
      {/each}
    </div>
  </div>
  
  <!-- Train / Val Split -->
  <div class="section-card">
    <h3>Train / Val Split</h3>
    <div class="split-bars">
      <div class="split-bar">
        <div class="split-label">Train:</div>
        <div class="split-meter">
          <div class="split-fill train" style="width: 75%;"></div>
        </div>
        <div class="split-value">18 (75%)</div>
      </div>
      <div class="split-bar">
        <div class="split-label">Val:</div>
        <div class="split-meter">
          <div class="split-fill val" style="width: 25%;"></div>
        </div>
        <div class="split-value">6 (25%)</div>
      </div>
    </div>
    <p class="split-note">Next 12 val will send S3 bucket for labeling</p>
  </div>
  
  <!-- Export Options -->
  <div class="section-card">
    <h3>📋 Export Full Dataset (.zip)</h3>
    <div class="export-actions">
      <button class="btn-export">🔗 Export Verified Only</button>
      <button class="btn-export secondary">✓ Export All</button>
    </div>
  </div>
  
  <!-- Notification Setup -->
  <div class="section-card">
    <h3>🔔 Notification Setup</h3>
    <div class="notification-form">
      <div class="form-field">
        <label>ntfy.sh — instant push, free</label>
        <input type="text" value="Severity 6/10 and hit → wake your team" class="form-input" readonly/>
      </div>
      <button class="btn-test">Send Test Push</button>
    </div>
    
    <div class="notification-form">
      <div class="form-field">
        <label>Telegram</label>
        <input type="text" placeholder="token / it-etc converted" class="form-input"/>
      </div>
    </div>
  </div>
</div>

<style>
  .dataset-page {
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
    margin-bottom: 0.25rem;
  }
  
  .subtitle {
    color: var(--text-muted);
    font-size: 0.875rem;
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .stat-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1.5rem;
    text-align: center;
  }
  
  .stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }
  
  .stat-value.need-review {
    color: var(--amber);
  }
  
  .stat-label {
    color: var(--text-muted);
    font-size: 0.875rem;
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
    margin-bottom: 0.75rem;
  }
  
  .section-subtitle {
    color: var(--text-muted);
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }
  
  .distribution-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .distribution-item {
    display: grid;
    grid-template-columns: 2fr 3fr auto;
    gap: 1rem;
    align-items: center;
  }
  
  .item-label {
    font-size: 0.875rem;
  }
  
  .item-bar {
    height: 1.5rem;
    background: var(--bg-elevated);
    border-radius: 0.25rem;
    overflow: hidden;
  }
  
  .bar-fill {
    height: 100%;
    transition: width 0.5s ease;
  }
  
  .item-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    text-align: right;
  }
  
  .animal-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .animal-tag {
    padding: 0.5rem 1rem;
    background: var(--amber-bg);
    color: var(--amber);
    border-radius: 0.375rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
  }
  
  .split-bars {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  
  .split-bar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1rem;
    align-items: center;
  }
  
  .split-label {
    font-size: 0.875rem;
    font-weight: 500;
  }
  
  .split-meter {
    height: 1.5rem;
    background: var(--bg-elevated);
    border-radius: 0.25rem;
    overflow: hidden;
  }
  
  .split-fill {
    height: 100%;
    transition: width 0.5s ease;
  }
  
  .split-fill.train {
    background: var(--green);
  }
  
  .split-fill.val {
    background: var(--blue);
  }
  
  .split-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
  }
  
  .split-note {
    color: var(--text-muted);
    font-size: 0.75rem;
  }
  
  .export-actions {
    display: flex;
    gap: 0.75rem;
  }
  
  .btn-export {
    padding: 0.75rem 1.5rem;
    background: var(--blue);
    border: none;
    border-radius: 0.375rem;
    color: #fff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  .btn-export:hover {
    opacity: 0.9;
  }
  
  .btn-export.secondary {
    background: var(--green);
  }
  
  .notification-form {
    margin-bottom: 1rem;
  }
  
  .form-field {
    margin-bottom: 0.5rem;
  }
  
  .form-field label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }
  
  .form-input {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: var(--bg-page);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
  }
  
  .btn-test {
    padding: 0.5rem 1rem;
    background: transparent;
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-test:hover {
    background: var(--bg-elevated);
  }
</style>
