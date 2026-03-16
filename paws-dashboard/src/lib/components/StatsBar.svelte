<script lang="ts">
  export let stats;
</script>

<div class="grid grid-cols-4 gap-4 p-4 bg-gray-900 text-white rounded-lg shadow font-mono text-sm">
  <div class="flex flex-col">
    <span class="text-gray-400">Total Detections</span>
    <span class="text-2xl font-bold">{stats.total_detections}</span>
  </div>
  <div class="flex flex-col">
    <span class="text-green-400">Threats Confirmed</span>
    <span class="text-2xl font-bold">{stats.threats_confirmed}</span>
  </div>
  <div class="flex flex-col">
    <span class="text-yellow-400">Threats Dismissed</span>
    <span class="text-2xl font-bold">{stats.threats_dismissed}</span>
  </div>
  <div class="flex flex-col">
    <span class="text-blue-400">Avg Pipeline</span>
    <span class="text-2xl font-bold">{stats.avg_pipeline_ms} <span class="text-sm font-normal text-blue-300">ms</span></span>
  </div>
</div>
