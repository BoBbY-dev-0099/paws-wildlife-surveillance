<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { Camera, Activity, Brain, Network, Radio, AlertTriangle, Volume2, Phone, X, Plus, Trash2, Edit2, Save, Play, Square } from 'lucide-svelte';
  import { API_BASE_URL } from '$lib/config';
  
  // Dynamic import for Hls to prevent SSR crashes
  let Hls: any;
  
  let cameras: any[] = [];
  let selectedCamera: string | null = null;
  let pipelineLog: any[] = [];
  let incidents: any[] = [];
  let activeThreat: any = null;
  let eventSource: EventSource | null = null;
  let showAddStream = false;
  let editingStream: any = null;
  let videoElement: HTMLVideoElement | null = null;
  let hlsInstance: any = null;
  let streamLoading = false;
  let streamError = '';
  let inferenceInProgress = new Set<string>();
  
  // Reactive states
  $: activeStreamObj = cameras.find(c => c.id === selectedCamera) || null;
  $: latestStatus = pipelineLog.length > 0 ? pipelineLog[pipelineLog.length - 1].message : null;
  
  // Watch for camera changes to setup player
  $: if (activeStreamObj && !activeStreamObj.active) {
    // Note: use a small timeout to ensure videoElement is bound
    setTimeout(() => setupVideoPlayer(), 50);
  }
  
  // Add/Edit Stream Form
  let streamForm = {
    name: '',
    url: '',
    type: 'RTSP'
  };
  let isSavingStream = false;

  // Auto-detect YouTube links
  $: if (streamForm.url && (streamForm.url.includes('youtube.com') || streamForm.url.includes('youtu.be'))) {
    if (streamForm.type !== 'HTTP') {
      streamForm.type = 'HTTP';
    }
  }
  
  async function loadCameras() {
    try {
      const res = await fetch('${API_BASE_URL}/api/streams');
      if (res.ok) {
        cameras = await res.json();
        if (!selectedCamera && cameras.length > 0) {
          selectCamera(cameras[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load cameras:', err);
    }
  }
  
  function selectCamera(cameraId) {
    selectedCamera = cameraId;
    pipelineLog = [];
    streamError = '';
    
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
  }
  
  function setupVideoPlayer(urlOverride = null) {
    if (!videoElement) return;
    
    // Default to stream URL if no override provided
    const url = urlOverride || activeStreamObj?.url;
    if (!url) return;
    
    const type = activeStreamObj?.type || 'HLS';
    
    console.log('🎥 Setting up video player for:', url);
    
    // Clean up old HLS instance
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    
    streamLoading = true;
    streamError = '';
    
    // If it's a Modal MJPEG stream
    if (url.includes('modal.run')) {
      console.log('🖼️ Using Modal MJPEG stream');
      videoElement.src = url;
      videoElement.onloadeddata = () => { streamLoading = false; };
      videoElement.onerror = () => { 
        streamLoading = false; 
        streamError = 'Modal stream connection failed.'; 
      };
      videoElement.play().catch(e => console.error('Modal auto-play failed', e));
      return;
    }
    
    // Only attempt video playback for HLS or HTTP video formats
    if (type === 'HLS' || url.endsWith('.m3u8')) {
      if (Hls && Hls.isSupported()) {
        hlsInstance = new Hls({ debug: false });
        hlsInstance.loadSource(url);
        hlsInstance.attachMedia(videoElement);
        hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
          streamLoading = false;
          videoElement?.play().catch((e: any) => console.error('Video auto-play failed', e));
        });
        hlsInstance.on(Hls.Events.ERROR, (event: any, data: any) => {
          if (data.fatal) {
            streamLoading = false;
            streamError = 'Stream unavailable. Retrying...';
            setTimeout(() => setupVideoPlayer(urlOverride), 3000);
          }
        });
      } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
        // Native Safari HLS support
        videoElement.src = url;
        videoElement.onloadedmetadata = () => {
          streamLoading = false;
          videoElement?.play().catch((e: any) => console.error('Native auto-play failed', e));
        };
        videoElement.onerror = () => {
          streamLoading = false;
          streamError = 'Stream error. Check the URL.';
        };
      } else {
        streamLoading = false;
        streamError = 'HLS not supported in this browser.';
      }
    } else if (type === 'HTTP' || url.endsWith('.mp4')) {
      videoElement.src = url;
      videoElement.onloadeddata = () => { streamLoading = false; };
      videoElement.onerror = () => { streamLoading = false; streamError = 'Video load failed.'; };
      videoElement.play().catch((e: any) => console.error('HTTP auto-play failed', e));
    } else {
      // RTSP or unknown — can't be played in browser directly
      streamLoading = false;
    }
  }
  
  async function startInference(streamId) {
    if (inferenceInProgress.has(streamId)) return;
    inferenceInProgress.add(streamId);
    inferenceInProgress = inferenceInProgress; // trigger reactivity
    
    // Optimistically set loading state
    streamLoading = true;
    streamError = '';
    pipelineLog = [{
      step: 'init',
      message: '🚀 Requesting inference start from backend...',
      timestamp: new Date()
    }];
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/streams/${streamId}/start`, {
        method: 'POST'
      });
      
        if (res.ok) {
        const data = await res.json();
        console.log('Inference started for', streamId, 'modal_url:', data.modal_url);
        
        cameras = cameras.map(c => c.id === streamId ? { ...c, active: true, modal_url: data.modal_url } : c);
        streamLoading = false;
      } else {
        const error = await res.json();
        alert(`Failed to start inference: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error starting inference:', err);
      alert('Error starting inference');
    } finally {
      inferenceInProgress.delete(streamId);
      inferenceInProgress = inferenceInProgress;
    }
  }
  
  async function stopInference(streamId) {
    if (inferenceInProgress.has(streamId)) return;
    inferenceInProgress.add(streamId);
    inferenceInProgress = inferenceInProgress;
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/streams/${streamId}/stop`, {
        method: 'POST'
      });
      
      if (res.ok) {
        console.log('Inference stopped for', streamId);
        await loadCameras();
      } else {
        alert('Failed to stop inference');
      }
    } catch (err) {
      console.error('Error stopping inference:', err);
      alert('Error stopping inference');
    } finally {
      inferenceInProgress.delete(streamId);
      inferenceInProgress = inferenceInProgress;
    }
  }
  
  async function addNewStream() {
    if (!streamForm.name.trim()) {
      alert('Please enter a stream name');
      return;
    }
    
    isSavingStream = true;
    try {
      const res = await fetch('${API_BASE_URL}/api/streams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(streamForm)
      });
      
      if (res.ok) {
        const data = await res.json();
        console.log('Stream added:', data);
        showAddStream = false;
        streamForm = { name: '', url: '', type: 'RTSP' };
        await loadCameras();
      } else {
        const error = await res.json();
        alert(`Failed to add stream: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error adding stream:', err);
      alert('Error adding stream');
    } finally {
      isSavingStream = false;
    }
  }
  
  async function deleteStream(streamId) {
    if (!confirm('Are you sure you want to delete this stream?')) {
      return;
    }
    
    try {
      // Stop inference first if active
      const camera = cameras.find(c => c.id === streamId);
      if (camera?.active) {
        await stopInference(streamId);
      }
      
      const res = await fetch(`${API_BASE_URL}/api/streams/${streamId}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        console.log('Stream deleted');
        if (selectedCamera === streamId) {
          selectedCamera = null;
        }
        await loadCameras();
      } else {
        alert('Failed to delete stream');
      }
    } catch (err) {
      console.error('Error deleting stream:', err);
      alert('Error deleting stream');
    }
  }
  
  async function fetchIncidents() {
    try {
      const res = await fetch('${API_BASE_URL}/api/incidents');
      if (res.ok) {
        const data = await res.json();
        incidents = data;
        activeThreat = incidents.find(i => isRecent(i.timestamp) && i.severity_score >= 6);
      }
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    }
  }
  
  function isRecent(timestamp) {
    const diff = Date.now() - new Date(timestamp).getTime();
    return diff < 15 * 60 * 1000;
  }
  
  function timeAgo(timestamp) {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }
  
  function connectSSE() {
    if (eventSource) {
      eventSource.close();
    }
    
    eventSource = new EventSource('${API_BASE_URL}/api/sse');
    
    eventSource.addEventListener('pipeline', (event) => {
      console.log('📊 Pipeline event raw:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed pipeline data:', data);
        const cid = data.camera_id || (data.data && data.data.camera_id);
        
        // Normalize comparison for safety
        const isMatch = cid && selectedCamera && String(cid).toLowerCase() === String(selectedCamera).toLowerCase();
        
        if (isMatch || !cid) {
          pipelineLog = [...pipelineLog, {
            step: data.step || 'info',
            message: data.message || 'Processing...',
            elapsed_ms: data.elapsed_ms || 0,
            timestamp: data.timestamp ? new Date(data.timestamp) : new Date()
          }];
          if (pipelineLog.length > 50) {
            pipelineLog = pipelineLog.slice(-50);
          }
        }
        
        // Final sync when pipeline completes
        if (data.step === 'complete') {
          fetchIncidents();
        }
      } catch (err) {
        console.error('Failed to parse pipeline event:', err);
      }
    });
    
    eventSource.addEventListener('detection', (event) => {
      console.log('🔔 Detection event raw:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed detection data:', data);
        activeThreat = data;
        
        const cid = data.camera_id || (data.data && data.data.camera_id);
        const isMatch = cid && selectedCamera && String(cid).toLowerCase() === String(selectedCamera).toLowerCase();

        if (isMatch || !cid) {
          pipelineLog = [...pipelineLog, {
            step: 'yolo',
            message: data.message || `Object detected: ${data.animal || 'unknown'}`,
            timestamp: data.timestamp ? new Date(data.timestamp) : new Date()
          }];
          if (pipelineLog.length > 50) {
            pipelineLog = pipelineLog.slice(-50);
          }
        }
        
        // Refresh list to keep it in sync
        fetchIncidents();
      } catch (err) {
        console.error('Error in detection listener:', err);
      }
    });

    eventSource.addEventListener('nova_analysis', (event) => {
      console.log('🧠 Nova analysis event raw:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('Parsed nova analysis data:', data);
        
        if (activeThreat) {
          activeThreat = {
            ...activeThreat,
            severity_score: data.severity_score || data.severity || 0,
            nova_analysis: {
              behavior: data.reasoning || data.behavior || '',
              recommendation: data.recommended_action || data.recommendation || '',
              nepali: data.nepali_translation || data.nepali || ''
            }
          };
        }
        
        const cid = data.camera_id || (data.data && data.data.camera_id);
        const isMatch = cid && selectedCamera && String(cid).toLowerCase() === String(selectedCamera).toLowerCase();

        if (isMatch || !cid) {
          pipelineLog = [...pipelineLog, {
            step: data.step || 'nova',
            message: data.message || 'Nova analysis complete.',
            elapsed_ms: data.elapsed_ms || 0,
            timestamp: data.timestamp ? new Date(data.timestamp) : new Date()
          }];
          if (pipelineLog.length > 50) {
            pipelineLog = pipelineLog.slice(-50);
          }
        }
        
        // Refresh incidents to show behavior/severity
        fetchIncidents();
      } catch (err) {
        console.error('Error in nova_analysis listener:', err);
      }
    });
    
    eventSource.addEventListener('heartbeat', (event) => {
      console.log('SSE heartbeat:', event.data);
    });
    
    eventSource.onerror = (err) => {
      console.error('SSE error:', err);
      eventSource.close();
      setTimeout(() => {
        connectSSE();
      }, 5000);
    };
  }
  
  onMount(async () => {
    // Load Hls dynamically on mount
    if (browser) {
      const HlsModule = await import('hls.js');
      Hls = HlsModule.default;
    }

    loadCameras();
    fetchIncidents();
    connectSSE();
    
    // Auto-refresh the MJPEG stream if the user switches tabs and comes back
    // (Browsers pause background images, breaking the stream)
    let lastHiddenAt = 0;
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        lastHiddenAt = Date.now();
      } else if (document.visibilityState === 'visible' && activeStreamObj?.active) {
        if (Date.now() - lastHiddenAt > 2000) {
          console.log('Tab visible again, refreshing stream...');
          loadCameras();
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    const interval = setInterval(() => {
      fetchIncidents();
    }, 30000);
    
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (eventSource) {
        eventSource.close();
      }
      if (hlsInstance) {
        hlsInstance.destroy();
      }
    };
  });
</script>

<div class="live-feed">
  <!-- Camera Management Header -->
  <div class="camera-management">
    <div class="camera-selector">
      {#each cameras as cam}
        <div class="camera-card {selectedCamera === cam.id ? 'active' : ''}">
          <button
            class="camera-btn"
            on:click={() => selectCamera(cam.id)}
          >
            <Camera size={16} />
            <span>{cam.name}</span>
            <span class="cam-type">{cam.type}</span>
            {#if cam.active}
              <span class="status-dot active" title="Inference running"></span>
            {/if}
          </button>
          
          <div class="camera-actions">
            {#if cam.url}
              {#if cam.active}
                <button
                  class="action-btn stop"
                  class:loading={inferenceInProgress.has(cam.id)}
                  on:click={() => stopInference(cam.id)}
                  disabled={inferenceInProgress.has(cam.id)}
                  title="Stop inference"
                >
                  {#if inferenceInProgress.has(cam.id)}
                    <div class="mini-spinner"></div>
                  {:else}
                    <Square size={14} />
                  {/if}
                </button>
              {:else}
                <button
                  class="action-btn start"
                  class:loading={inferenceInProgress.has(cam.id)}
                  on:click={() => startInference(cam.id)}
                  disabled={inferenceInProgress.has(cam.id)}
                  title="Start Modal inference"
                >
                  {#if inferenceInProgress.has(cam.id)}
                    <div class="mini-spinner"></div>
                  {:else}
                    <Play size={14} />
                  {/if}
                </button>
              {/if}
            {/if}
            <button
              class="action-btn delete"
              on:click={() => deleteStream(cam.id)}
              title="Delete stream"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      {/each}
    </div>
    
    <button class="add-stream-btn" on:click={() => showAddStream = !showAddStream}>
      <Plus size={16} />
      Add Stream
    </button>
  </div>
  
  <!-- Add Stream Form -->
  {#if showAddStream}
    <div class="stream-form">
      <div class="form-header">
        <h3>Add New Stream</h3>
        <button class="close-btn" on:click={() => showAddStream = false}>
          <X size={16} />
        </button>
      </div>
      
      <div class="form-body">
        <div class="form-field">
          <label>Stream Name</label>
          <input
            type="text"
            bind:value={streamForm.name}
            placeholder="e.g., North Perimeter"
          />
        </div>
        
        <div class="form-field">
          <label>Stream URL</label>
          <input
            type="text"
            bind:value={streamForm.url}
            placeholder="rtsp://... or http://... or camera:0"
          />
        </div>
        
        <div class="form-field">
          <label>Type</label>
          <select bind:value={streamForm.type}>
            <option value="RTSP">RTSP (IP Camera)</option>
            <option value="HLS">HLS (.m3u8)</option>
            <option value="HTTP">HTTP / YouTube</option>
            <option value="WEBCAM">Local Webcam (camera:0)</option>
          </select>
        </div>
        
        <div class="form-actions">
          <button class="btn-cancel" on:click={() => showAddStream = false}>Cancel</button>
          <button class="btn-save" on:click={addNewStream} disabled={isSavingStream}>
            {#if isSavingStream}
              <div class="mini-spinner"></div>
            {:else}
              <Save size={16} />
            {/if}
            {isSavingStream ? 'Adding...' : 'Add Stream'}
          </button>
        </div>
      </div>
    </div>
  {/if}
  
  <div class="feed-layout">
    <!-- Main Content -->
    <div class="main-content">
      <!-- Video Player Section -->
      <div class="video-container">
        {#if !activeStreamObj}
          <div class="no-stream">
            <Camera size={48} />
            <p>Select a camera to view feed</p>
          </div>
        {:else}
          <!-- Direct MJPEG stream from Modal with bounding boxes -->
          {#if activeStreamObj.active && activeStreamObj.modal_url}
            <img 
              class="live-video visible"
              src={activeStreamObj.modal_url}
              alt={`${activeStreamObj.name} - AI Inference Feed`}
            />
          {:else if (activeStreamObj.type === 'HLS' || activeStreamObj.type === 'HTTP') && !activeStreamObj.active}
            <video
              bind:this={videoElement}
              class="live-video raw-feed visible"
              autoplay
              muted
              playsinline
              crossorigin="anonymous"
            ></video>
          {:else if !activeStreamObj.active}
            <div class="ready-placeholder">
              <div class="placeholder-icon">
                <Play size={48} />
              </div>
              <h3>Ready to Start</h3>
              <p>Stream: {activeStreamObj.name}</p>
              <p class="subtitle">Click the Start button above to begin inference and view feed</p>
            </div>
          {/if}
          
          {#if activeStreamObj.active}
            <div class="inference-badge pulse">AI INFERENCE ACTIVE</div>
          {/if}
        {/if}

        <!-- Loading overlay -->
        {#if streamLoading && activeStreamObj}
          <div class="stream-loading-overlay">
            <div class="spinner"></div>
            <div class="loading-status">
              <span>{latestStatus || 'Connecting to stream…'}</span>
              {#if latestStatus && latestStatus.includes('YouTube')}
                 <span class="sub-status">This may take 5-10 seconds...</span>
              {/if}
            </div>
          </div>
        {/if}

        <!-- Error overlay -->
        {#if streamError && !streamLoading}
          <div class="stream-error-overlay">
            <AlertTriangle size={32} />
            <span>{streamError}</span>
          </div>
        {/if}
      </div>
      <!-- Active Threat Alert -->
      {#if activeThreat}
        <div class="threat-alert">
          <div class="alert-header">
            <AlertTriangle size={20} />
            <div class="alert-info">
              <strong>{activeThreat.animal.toUpperCase()}</strong>
              <span>at {activeThreat.location}</span>
              <span>·</span>
              <span class="severity">Severity {activeThreat.severity_score}/10</span>
              <span>·</span>
              <span>{activeThreat.behavior}</span>
              <span>·</span>
              <span class="time">{timeAgo(activeThreat.timestamp)}</span>
            </div>
          </div>
          <div class="alert-actions">
            <button class="btn-action deterrent">
              <Volume2 size={16} />
              Sound Deterrent
            </button>
            <button class="btn-action call">
              <Phone size={16} />
              Call Authorities
            </button>
            <button class="btn-action dismiss">
              <X size={16} />
              False Alarm
            </button>
          </div>
        </div>
      {/if}
      
      <!-- Pipeline Log (Fix 3: Terminal Style) -->
      <div class="pipeline-panel terminal-style">
        <div class="panel-header terminal-header">
          <div class="terminal-dots">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
          </div>
          <span>Live Pipeline - {cameras.find(c => c.id === selectedCamera)?.name || 'TRACE'}</span>
        </div>
        <div class="log-content terminal-body">
          {#if pipelineLog.length === 0}
            <div class="log-empty">
              <span class="cursor">_</span>
              <p>Waiting for detection packets...</p>
            </div>
          {:else}
            {#each pipelineLog as log}
              <div class="log-entry terminal-row">
                <span class="log-time">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                <span class="log-step">{log.step.toUpperCase()}</span>
                <span class="log-arrow">»</span>
                <span class="log-message">{log.message}</span>
                {#if log.elapsed_ms}
                  <span class="log-duration">{log.elapsed_ms}ms</span>
                {/if}
              </div>
            {/each}
          {/if}
        </div>
      </div>

      <!-- Alert Delivery Card (Fix 4) -->
      {#if activeThreat}
        <div class="alert-delivery-card">
          <div class="panel-header">
             <Network size={16} />
             <span>Alert Delivery Status</span>
          </div>
          <div class="delivery-grid">
            <div class="delivery-item {activeThreat.alerts_sent?.ntfy ? 'sent' : 'pending'}">
              <span class="status-dot"></span> ntfy.sh
            </div>
            <div class="delivery-item {activeThreat.alerts_sent?.telegram ? 'sent' : 'pending'}">
              <span class="status-dot"></span> Telegram
            </div>
            <div class="delivery-item {activeThreat.neighbors_notified > 0 ? 'sent' : 'pending'}">
              <span class="status-dot"></span> Farm Mesh
            </div>
            <div class="delivery-item {activeThreat.deterrent_fired ? 'sent' : 'pending'}">
              <span class="status-dot"></span> Deterrent
            </div>
          </div>
        </div>
      {/if}
    </div>
    
    <!-- Sidebar -->
    <div class="sidebar">
      <!-- AI Analysis (Fix 2: Redesign) -->
      {#if activeThreat}
        <div class="ai-panel">
          <div class="panel-header">
            <Brain size={18} />
            <span>Nova AI Analysis</span>
          </div>
          <div class="ai-content">
            {#if activeThreat.nova_analysis}
              <div class="nova-status">
                <span class="brain-icon">🧠</span>
                <span class="nova-label">Nova 2 Lite</span>
                <span class="check">✓</span>
                <span class="complete">Complete</span>
                {#if activeThreat.pipeline_ms}
                  <span class="time">{ (activeThreat.pipeline_ms / 1000).toFixed(1) }s</span>
                {/if}
              </div>

              <div class="analysis-section">
                <div class="section-label">What it's doing:</div>
                <div class="quote-value">"{activeThreat.nova_analysis.behavior || 'Elephant detected near fence'}"</div>
              </div>
              
              <div class="analysis-section">
                <div class="section-label">Threat level:</div>
                <div class="threat-visual">
                  <div class="threat-meter-v2">
                    {#each Array(10) as _, i}
                      <div class="meter-segment {i < activeThreat.severity_score ? 'active' : ''}"></div>
                    {/each}
                  </div>
                  <span class="severity-tag">{activeThreat.severity_score}/10 {activeThreat.severity_score >= 7 ? 'HIGH' : 'MED'}</span>
                </div>
              </div>
              
              <div class="analysis-section">
                <div class="section-label">Deterrent: </div>
                <div class="deterrent-box">
                  <div class="rec-action">{activeThreat.nova_analysis.recommendation || 'Ultrasonic burst'}</div>
                  <div class="rec-desc">"Fires 15-25kHz — inaudible to humans"</div>
                </div>
              </div>

              <div class="analysis-section">
                <div class="section-label">Alert sent in:</div>
                <div class="lang-switch">
                  <button class="lang-btn active">[EN]</button>
                  <button class="lang-btn">[HI]</button>
                  <button class="lang-btn">[SW]</button>
                  <button class="lang-btn">[ES]</button>
                  <span class="switch-hint">— click to switch</span>
                </div>
                <div class="quote-value translated">
                  "{activeThreat.nova_analysis.nepali || '⚠️ Elephant approaching fence!'}"
                </div>
              </div>

              <button class="voice-alert-btn">
                <Volume2 size={16} />
                ▶ Play voice alert
              </button>

            {/if}
          </div>
        </div>
      {/if}
      <div class="incidents-card">
        <div class="card-header">
          <AlertTriangle size={18} />
          <span>Recent Incidents</span>
        </div>
        <div class="incidents-list">
          {#if incidents.length === 0}
            <div class="empty-state">
              <p>No incidents recorded</p>
            </div>
          {:else}
            {#each incidents.slice(0, 10) as incident}
              <div class="incident-item">
                <div class="incident-severity severity-{incident.severity_score}">
                  <span class="sev-label">SEV</span> {incident.severity_score}
                </div>
                <div class="incident-info">
                  <div class="incident-title">{incident.animal} · approaching · Sev {incident.severity_score}/10</div>
                  <div class="incident-meta">{incident.behavior || 'Behavior being tracked'} · {timeAgo(incident.timestamp)}</div>
                </div>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .live-feed {
    padding: 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
  }
  
  /* Video Player */
  .video-container {
    background: #000;
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    aspect-ratio: 16/9;
    overflow: hidden;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .live-video {
    width: 100%;
    height: 100%;
    object-fit: contain;
    transition: opacity 0.3s ease;
  }
  
  .hidden {
    opacity: 0;
    pointer-events: none;
    position: absolute;
  }
  
  .visible {
    opacity: 1;
  }

  .loading-status {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    text-align: center;
  }
  
  .sub-status {
    font-size: 0.75rem;
    opacity: 0.7;
    font-style: italic;
  }
  
  /* Loading overlay */
  .stream-loading-overlay,
  .stream-error-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 0.75rem;
  }
  
  .stream-loading-overlay {
    background: rgba(0, 0, 0, 0.75);
    color: #fff;
    backdrop-filter: blur(4px);
  }
  
  .stream-error-overlay {
    background: rgba(220, 38, 38, 0.25);
    color: var(--red, #ef4444);
    border: 1px solid rgba(220, 38, 38, 0.5);
  }
  
  .spinner {
    width: 2.5rem;
    height: 2.5rem;
    border: 3px solid rgba(255, 255, 255, 0.2);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .analysis-pending {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 1.5rem;
    color: var(--text-muted);
  }

  .nepali-box {
    margin-top: 1rem;
    padding: 0.75rem;
    background: rgba(16, 185, 129, 0.1);
    border-left: 3px solid var(--green);
    border-radius: 0.25rem;
  }

  .nepali-text {
    font-size: 1.1rem;
    font-weight: 500;
  }

  .mini-spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  .action-btn.loading {
    opacity: 0.7;
    cursor: wait;
  }

  .ready-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: var(--text-primary);
    text-align: center;
    padding: 2rem;
  }

  .ready-placeholder h3 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0;
  }

  .ready-placeholder .subtitle {
    font-size: 0.875rem;
    color: var(--text-muted);
    max-width: 300px;
  }

  .placeholder-icon {
    width: 6rem;
    height: 6rem;
    background: var(--bg-elevated);
    border: 2px solid var(--bg-border);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--green);
    margin-bottom: 0.5rem;
  }

  .no-stream {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    color: var(--text-muted);
  }
  
  .no-stream p {
    font-size: 1.125rem;
    font-weight: 500;
  }
  
  .inference-badge {
    position: absolute;
    top: 1rem;
    left: 1rem;
    background: rgba(220, 38, 38, 0.9);
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }
  
  .pulse {
    animation: badge-pulse 2s infinite;
  }
  
  @keyframes badge-pulse {
    0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(220, 38, 38, 0); }
    100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
  }
  
  /* Camera Management */
  .camera-management {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    align-items: flex-start;
  }
  
  .camera-selector {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    flex: 1;
  }
  
  .camera-card {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--bg-card);
    border: 2px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 0.5rem;
    transition: all 0.2s;
  }
  
  .camera-card:hover {
    border-color: var(--blue);
  }
  
  .camera-card.active {
    border-color: var(--blue);
    background: var(--blue-bg);
  }
  
  .camera-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.5rem;
    background: transparent;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
  }
  
  .cam-type {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
  
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
  }
  
  .status-dot.active {
    background: var(--green);
    animation: pulse-dot 2s ease-in-out infinite;
  }
  
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  
  .camera-actions {
    display: flex;
    gap: 0.25rem;
    margin-left: auto;
  }
  
  .action-btn {
    padding: 0.375rem;
    background: transparent;
    border: 1px solid var(--bg-border);
    border-radius: 0.25rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .action-btn.start {
    color: var(--green);
    border-color: var(--green);
  }
  
  .action-btn.start:hover {
    background: var(--green);
    color: #fff;
  }
  
  .action-btn.stop {
    color: var(--amber);
    border-color: var(--amber);
  }
  
  .action-btn.stop:hover {
    background: var(--amber);
    color: #000;
  }
  
  .action-btn.delete {
    color: var(--red);
    border-color: var(--red);
  }
  
  .action-btn.delete:hover {
    background: var(--red);
    color: #fff;
  }
  
  .add-stream-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--green);
    border: none;
    border-radius: 0.5rem;
    color: #fff;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }
  
  .add-stream-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
  }
  
  /* Stream Form */
  .stream-form {
    background: var(--bg-card);
    border: 2px solid var(--green);
    border-radius: 0.75rem;
    margin-bottom: 1.5rem;
    overflow: hidden;
  }
  
  .form-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    background: var(--green-bg);
    border-bottom: 1px solid var(--bg-border);
  }
  
  .form-header h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--green);
  }
  
  .close-btn {
    padding: 0.25rem;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 0.25rem;
    transition: all 0.2s;
  }
  
  .close-btn:hover {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }
  
  .form-body {
    padding: 1.5rem;
  }
  
  .form-field {
    margin-bottom: 1rem;
  }
  
  .form-field label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
  }
  
  .form-field input,
  .form-field select {
    width: 100%;
    padding: 0.625rem 0.75rem;
    background: var(--bg-elevated);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-primary);
    font-size: 0.875rem;
    font-family: inherit;
  }
  
  .form-field input:focus,
  .form-field select:focus {
    outline: none;
    border-color: var(--green);
  }
  
  .form-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
    margin-top: 1.5rem;
  }
  
  .btn-cancel,
  .btn-save {
    padding: 0.625rem 1rem;
    border: none;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-cancel {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--bg-border);
  }
  
  .btn-cancel:hover {
    background: var(--bg-border);
  }
  
  .btn-save {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--green);
    color: #fff;
  }
  
  .btn-save:hover {
    transform: translateY(-1px);
  }
  
  /* Feed Layout */
  .feed-layout {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 1.5rem;
  }
  
  @media (max-width: 1024px) {
    .feed-layout {
      grid-template-columns: 1fr;
    }
  }
  
  .main-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }
  
  /* Threat Alert */
  .threat-alert {
    background: var(--red-bg);
    border: 2px solid var(--red);
    border-radius: 0.75rem;
    padding: 1.5rem;
    animation: pulse-alert 2s ease-in-out infinite;
  }
  
  @keyframes pulse-alert {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  }
  
  .alert-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  
  .alert-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    font-size: 0.875rem;
  }
  
  .severity {
    color: var(--red);
    font-weight: 600;
  }
  
  .time {
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
  }
  
  .alert-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }
  
  .btn-action {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1rem;
    border: none;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-action.deterrent {
    background: var(--amber);
    color: #000;
  }
  
  .btn-action.call {
    background: var(--red);
    color: #fff;
  }
  
  .btn-action.dismiss {
    background: var(--bg-elevated);
    color: var(--text-primary);
    border: 1px solid var(--bg-border);
  }
  
  /* Panels */
  .pipeline-panel,
  .ai-panel {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    overflow: hidden;
  }
  
  .panel-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--bg-border);
    font-weight: 600;
  }
  
  .log-content {
    padding: 1.5rem;
    background: var(--bg-page);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    max-height: 500px;
    overflow-y: auto;
  }
  
  .log-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 3rem;
    text-align: center;
    color: var(--text-muted);
  }
  
  .log-entry {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    line-height: 1.6;
  }
  
  .log-time {
    color: var(--text-muted);
    min-width: 80px;
  }
  
  .log-step {
    color: var(--blue);
    min-width: 100px;
  }
  
  .log-message {
    color: var(--text-primary);
    flex: 1;
  }
  
  /* AI Panel */
  .ai-content {
    padding: 1.5rem;
  }
  
  .analysis-field {
    margin-bottom: 1.25rem;
  }
  
  .analysis-field:last-child {
    margin-bottom: 0;
  }
  
  .field-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
    font-weight: 500;
  }
  
  .field-value {
    font-size: 0.875rem;
    color: var(--text-primary);
  }
  
  .threat-meter {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .meter-bar {
    flex: 1;
    height: 0.5rem;
    background: var(--bg-elevated);
    border-radius: 9999px;
    overflow: hidden;
  }
  
  .meter-fill {
    height: 100%;
    background: var(--amber);
    border-radius: 9999px;
    transition: width 0.5s ease;
  }
  
  .meter-value {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    min-width: 48px;
  }
  
  /* Sidebar */
  .incidents-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    overflow: hidden;
    position: sticky;
    top: 1rem;
  }
  
  .card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--bg-border);
    font-weight: 600;
  }
  
  .incidents-list {
    padding: 1rem;
    max-height: calc(100vh - 200px);
    overflow-y: auto;
  }
  
  .empty-state {
    padding: 2rem;
    text-align: center;
    color: var(--text-muted);
  }
  
  .incident-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    transition: background 0.2s;
    cursor: pointer;
  }
  
  .incident-item:hover {
    background: var(--bg-elevated);
  }
  
  .incident-severity {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
    flex-shrink: 0;
  }
  
  .incident-severity[class*="severity-1"],
  .incident-severity[class*="severity-2"],
  .incident-severity[class*="severity-3"] {
    background: var(--green-bg);
    color: var(--green);
  }
  
  .incident-severity[class*="severity-4"],
  .incident-severity[class*="severity-5"],
  .incident-severity[class*="severity-6"] {
    background: var(--amber-bg);
    color: var(--amber);
  }
  
  .incident-severity[class*="severity-7"],
  .incident-severity[class*="severity-8"],
  .incident-severity[class*="severity-9"],
  .incident-severity[class*="severity-10"] {
    background: var(--red-bg);
    color: var(--red);
  }
  
  .incident-info {
    flex: 1;
    min-width: 0;
  }
  
  .incident-title {
    font-size: 0.875rem;
    font-weight: 500;
    text-transform: capitalize;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 0.25rem;
  }
  
  .incident-meta {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  /* Terminal Style Pipeline (Fix 3) */
  .terminal-style {
    background: #0d1117;
    border: 1px solid #30363d;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }
  
  .terminal-header {
    background: #161b22;
    border-bottom: 1px solid #30363d;
    color: #8b949e;
    font-size: 0.75rem;
    padding: 0.5rem 1rem;
  }
  
  .terminal-dots {
    display: flex;
    gap: 0.4rem;
    margin-right: 0.8rem;
  }
  
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }
  .dot.red { background: #ff5f56; }
  .dot.yellow { background: #ffbd2e; }
  .dot.green { background: #27c93f; }
  
  .terminal-body {
    background: #0d1117;
    color: #e6edf3;
    padding: 1rem;
    min-height: 150px;
  }
  
  .terminal-row {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    margin-bottom: 0.25rem;
    border-bottom: none;
    opacity: 0.9;
    animation: fade-in-terminal 0.3s ease-out;
  }
  
  @keyframes fade-in-terminal {
    from { opacity: 0; transform: translateX(-5px); }
    to { opacity: 0.9; transform: translateX(0); }
  }
  
  .log-time { color: #58a6ff; }
  .log-step { color: #d2a8ff; font-weight: bold; }
  .log-arrow { color: #8b949e; }
  .log-message { color: #e6edf3; }
  .log-duration { color: #3fb950; font-style: italic; margin-left: auto; }
  
  .cursor {
    display: inline-block;
    width: 8px;
    height: 15px;
    background: #238636;
    animation: blink 1s step-end infinite;
    vertical-align: middle;
  }
  
  @keyframes blink {
    50% { opacity: 0; }
  }

  /* AI Panel (Fix 2) */
  .nova-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    font-family: 'JetBrains Mono', monospace;
  }
  
  .nova-label { font-weight: 700; color: #fff; }
  .check { color: #3fb950; font-weight: bold; }
  .complete { color: #3fb950; font-size: 0.8rem; }
  
  .analysis-section {
    margin-bottom: 1.5rem;
  }
  
  .section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }
  
  .quote-value {
    font-style: italic;
    color: var(--text-primary);
    background: var(--bg-elevated);
    padding: 0.75rem;
    border-radius: 0.5rem;
    border-left: 3px solid var(--blue);
    font-size: 0.9rem;
  }
  
  .threat-meter-v2 {
    display: flex;
    gap: 0.2rem;
    margin-bottom: 0.5rem;
  }
  
  .meter-segment {
    flex: 1;
    height: 8px;
    background: #30363d;
    border-radius: 2px;
  }
  
  .meter-segment.active {
    background: linear-gradient(to right, #f85149, #9e1515);
  }
  
  .severity-tag {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 800;
    font-size: 0.9rem;
    color: #f85149;
  }
  
  .deterrent-box {
    background: rgba(243, 156, 18, 0.1);
    border: 1px dashed var(--amber);
    padding: 1rem;
    border-radius: 0.5rem;
  }
  
  .rec-action { font-weight: 700; color: var(--amber); margin-bottom: 0.2rem; }
  .rec-desc { font-size: 0.75rem; color: var(--text-muted); }
  
  .lang-switch {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  
  .lang-btn {
    background: transparent;
    border: 1px solid #30363d;
    color: #8b949e;
    font-size: 0.75rem;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    cursor: pointer;
  }
  
  .lang-btn.active {
    background: var(--blue);
    color: #fff;
    border-color: var(--blue);
  }
  
  .switch-hint { font-size: 0.7rem; color: #8b949e; }
  
  .voice-alert-btn {
    width: 100%;
    margin-top: 0.5rem;
    background: var(--bg-elevated);
    border: 1px solid #30363d;
    color: #fff;
    padding: 0.75rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .voice-alert-btn:hover { background: #30363d; }
  
  /* Alert Delivery Status (Fix 4) */
  .alert-delivery-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    margin-top: 1rem;
    overflow: hidden;
  }
  
  .delivery-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    padding: 1rem;
  }
  
  .delivery-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-muted);
  }
  
  .delivery-item.sent { color: #3fb950; font-weight: 600; }
  
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #30363d;
  }
  
  .sent .status-dot {
    background: #3fb950;
    box-shadow: 0 0 8px #3fb950;
  }

  /* Incident Upgrade (Fix 5) */
  .incident-severity {
    width: auto !important;
    height: auto !important;
    padding: 0.4rem 0.6rem !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace;
  }
  
  .sev-label { font-size: 0.55rem; opacity: 0.7; margin-right: 2px; }
</style>
