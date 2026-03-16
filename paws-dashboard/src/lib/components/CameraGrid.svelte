<script lang="ts">
  export let cameras = [];

  function expandCamera(id) {
    console.log('Expand camera', id);
  }

  function fullscreen(id) {
    console.log('Fullscreen camera', id);
  }
</script>

<div class="camera-grid">
  {#each cameras as cam (cam.id)}
    <div 
      class="camera-tile {cam.hasAlert ? 'alert' : ''}"
      on:click={() => expandCamera(cam.id)}
      on:keydown={(e) => e.key === 'Enter' && expandCamera(cam.id)}
      role="button"
      tabindex="0"
    >
      <!-- Video feed -->
      <img src={cam.streamUrl} alt={cam.name} class="camera-feed" />
      
      <!-- Camera label overlay (bottom left) -->
      <div class="cam-label">
        <span class="cam-dot {cam.live ? 'live' : 'offline'}"></span>
        {cam.name}
      </div>
      
      <!-- Alert overlay (shown when threat on this camera) -->
      {#if cam.hasAlert}
        <div class="cam-alert-overlay">
          <span class="cam-alert-text">⚠ {cam.alertAnimal?.toUpperCase()}</span>
        </div>
      {/if}
      
      <!-- Fullscreen button -->
      <button 
        class="cam-fullscreen" 
        on:click|stopPropagation={() => fullscreen(cam.id)}
        title="Fullscreen"
      >
        ⛶
      </button>
    </div>
  {/each}
</div>

{#if cameras.length === 0}
  <div class="p-8 text-center rounded-lg" style="background: var(--bg-card); border: 1px dashed var(--bg-border); color: var(--text-muted);">
    <p class="text-sm">No cameras connected</p>
    <p class="text-xs mt-2">Configure camera streams in settings</p>
  </div>
{/if}
