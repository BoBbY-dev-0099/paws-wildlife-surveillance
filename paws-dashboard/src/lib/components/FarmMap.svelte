<script lang="ts">
  export let activeThreat = null;
  let radius = 2.5; // km
</script>

<div class="farm-map-card">
  <div class="map-header">
    <span>Farm Perimeter</span>
    <span class="map-radius">{radius}km radius</span>
  </div>
  
  <svg viewBox="0 0 300 200" class="farm-svg">
    <!-- Grid background -->
    <defs>
      <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--bg-border)" stroke-width="0.5"/>
      </pattern>
    </defs>
    <rect width="300" height="200" fill="url(#grid)"/>
    
    <!-- Farm boundary -->
    <rect 
      x="40" y="30" width="220" height="140" 
      fill="rgba(34,197,94,0.05)" 
      stroke="var(--green)" 
      stroke-width="1.5" 
      stroke-dasharray="6 3" 
      rx="4"
    />
    
    <!-- Farm label -->
    <text 
      x="150" y="22" 
      text-anchor="middle" 
      fill="var(--text-muted)" 
      font-size="10" 
      font-family="Inter"
    >
      Your Farm
    </text>
    
    <!-- Camera positions (4 corners) -->
    <g class="camera-markers">
      <circle cx="40" cy="30" r="5" fill="var(--blue)"/>
      <text x="48" y="26" fill="var(--text-secondary)" font-size="8" font-family="Inter">CAM 1</text>
      
      <circle cx="260" cy="30" r="5" fill="var(--blue)"/>
      <text x="222" y="26" fill="var(--text-secondary)" font-size="8" font-family="Inter">CAM 2</text>
      
      <circle cx="40" cy="170" r="5" fill="var(--blue)"/>
      <text x="48" y="180" fill="var(--text-secondary)" font-size="8" font-family="Inter">CAM 3</text>
      
      <circle cx="260" cy="170" r="5" fill="var(--blue)"/>
      <text x="222" y="180" fill="var(--text-secondary)" font-size="8" font-family="Inter">CAM 4</text>
    </g>
    
    <!-- Your farm center -->
    <circle cx="150" cy="100" r="6" fill="var(--green)"/>
    <text x="162" y="104" fill="var(--green)" font-size="9" font-family="Inter" font-weight="600">You</text>
    
    <!-- Threat location (only shown when threat active) -->
    {#if activeThreat}
      <circle cx={activeThreat.mapX} cy={activeThreat.mapY} r="8" fill="var(--red)" opacity="0.9">
        <animate attributeName="r" values="6;12;6" dur="1.5s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.9;0.4;0.9" dur="1.5s" repeatCount="indefinite"/>
      </circle>
      <text 
        x={activeThreat.mapX + 12} 
        y={activeThreat.mapY + 4} 
        fill="var(--red)" 
        font-size="10" 
        font-family="Inter" 
        font-weight="600"
      >
        {activeThreat.animal}
      </text>
    {/if}
  </svg>
  
  <input 
    type="range" 
    min="0.5" 
    max="5" 
    step="0.5" 
    bind:value={radius} 
    class="radius-slider w-full"
  />
  <div class="radius-label">{radius}km alert radius</div>
</div>
