<script>
  const neighbors = [
    { name: 'Tembo Holdings', distance: '8.7km', language: 'English', status: 'ntfy sent' },
    { name: 'Njozi Agriculture', distance: '6.1km', language: 'Swahili', status: 'ntfy sent' },
    { name: 'Okavango Fields', distance: '12.4km', language: 'English', status: 'ntfy sent' }
  ];
</script>

<div class="mesh-page">
  <div class="mesh-header">
    <h2>Farm Mesh</h2>
    <p class="mesh-subtitle">Alert neighboring smallholder farms in realtime</p>
  </div>
  
  <!-- Map Section -->
  <div class="map-section">
    <svg class="mesh-map" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
      <!-- Background -->
      <rect width="800" height="400" fill="var(--bg-elevated)" opacity="0.3"/>
      
      <!-- Alert Radius Circle -->
      <circle cx="400" cy="200" r="120" fill="none" stroke="var(--green)" stroke-width="2" stroke-dasharray="5,5" opacity="0.3"/>
      
      <!-- Your Farm (Center) -->
      <circle cx="400" cy="200" r="8" fill="var(--green)">
        <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite"/>
      </circle>
      <text x="400" y="225" text-anchor="middle" fill="var(--text-primary)" font-size="12">Your Farm</text>
      
      <!-- Neighbor Farms -->
      <circle cx="300" cy="150" r="6" fill="var(--amber)"/>
      <text x="300" y="140" text-anchor="middle" fill="var(--text-primary)" font-size="10">Tembo Holdings</text>
      
      <circle cx="500" cy="170" r="6" fill="var(--amber)"/>
      <text x="500" y="160" text-anchor="middle" fill="var(--text-primary)" font-size="10">Njozi Agriculture</text>
      
      <circle cx="350" cy="280" r="6" fill="var(--amber)"/>
      <text x="350" y="295" text-anchor="middle" fill="var(--text-primary)" font-size="10">Okavango Fields</text>
    </svg>
    
    <!-- Radius Slider -->
    <div class="radius-control">
      <label class="control-label">Radius:</label>
      <input type="range" min="0.5" max="5" step="0.1" value="1.4" class="radius-slider"/>
      <span class="radius-value">1.4km</span>
    </div>
  </div>
  
  <!-- Neighbors Table -->
  <div class="neighbors-section">
    <table class="neighbors-table">
      <thead>
        <tr>
          <th>Farm</th>
          <th>Distance</th>
          <th>Language</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {#each neighbors as neighbor}
          <tr>
            <td>{neighbor.name}</td>
            <td>{neighbor.distance}</td>
            <td>{neighbor.language}</td>
            <td><span class="status-sent">{neighbor.status}</span></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  
  <!-- Register Form -->
  <div class="register-section">
    <h3>Register Neighbor Farm</h3>
    <div class="register-form">
      <input type="text" placeholder="Farm name" class="form-input"/>
      <input type="text" placeholder="Lat" class="form-input"/>
      <input type="text" placeholder="Lon" class="form-input"/>
      <button class="btn-register">Register Farm</button>
    </div>
  </div>
</div>

<style>
  .mesh-page {
    padding: 1rem;
    max-width: 1000px;
    margin: 0 auto;
  }
  
  .mesh-header {
    margin-bottom: 1.5rem;
  }
  
  .mesh-header h2 {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  
  .mesh-subtitle {
    color: var(--text-muted);
    font-size: 0.875rem;
  }
  
  .map-section {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1.5rem;
  }
  
  .mesh-map {
    width: 100%;
    height: 300px;
    margin-bottom: 1rem;
  }
  
  .radius-control {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  
  .control-label {
    font-size: 0.875rem;
    font-weight: 500;
  }
  
  .radius-slider {
    flex: 1;
    height: 4px;
    background: var(--bg-elevated);
    border-radius: 2px;
    outline: none;
    -webkit-appearance: none;
  }
  
  .radius-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    background: var(--green);
    border-radius: 50%;
    cursor: pointer;
  }
  
  .radius-slider::-moz-range-thumb {
    width: 16px;
    height: 16px;
    background: var(--green);
    border-radius: 50%;
    cursor: pointer;
    border: none;
  }
  
  .radius-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
    font-weight: 600;
  }
  
  .neighbors-section {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1.5rem;
    overflow-x: auto;
  }
  
  .neighbors-table {
    width: 100%;
    border-collapse: collapse;
  }
  
  .neighbors-table thead th {
    text-align: left;
    padding: 0.75rem;
    border-bottom: 1px solid var(--bg-border);
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-muted);
  }
  
  .neighbors-table tbody td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--bg-border);
    font-size: 0.875rem;
  }
  
  .neighbors-table tbody tr:last-child td {
    border-bottom: none;
  }
  
  .status-sent {
    padding: 0.25rem 0.5rem;
    background: var(--green-bg);
    color: var(--green);
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
  }
  
  .register-section {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1rem;
  }
  
  .register-section h3 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }
  
  .register-form {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr auto;
    gap: 0.75rem;
  }
  
  @media (max-width: 768px) {
    .register-form {
      grid-template-columns: 1fr;
    }
  }
  
  .form-input {
    padding: 0.5rem 0.75rem;
    background: var(--bg-page);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
  }
  
  .form-input::placeholder {
    color: var(--text-muted);
  }
  
  .btn-register {
    padding: 0.5rem 1.5rem;
    background: var(--green);
    border: none;
    border-radius: 0.375rem;
    color: #fff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  .btn-register:hover {
    opacity: 0.9;
  }
</style>
