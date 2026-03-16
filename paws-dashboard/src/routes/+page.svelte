<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { Camera, Zap, Brain, Network, Radio, Moon, Sun, Sprout, ArrowRight, Shield } from 'lucide-svelte';
  
  let theme = 'dark';
  let activeRegion = 'Africa';
  let currentStep = 3; // Nova Embed highlighted by default
  
  const regions: Record<string, any> = {
    Africa: {
      animals: ['Elephant', 'Lion', 'Leopard', 'Hyena', 'Hippo'],
      languages: ['Swahili', 'Amharic', 'Hausa'],
      sample: '⚠️ Tembo anakaribia ua la kaskazini!'
    },
    Asia: {
      animals: ['Elephant', 'Tiger', 'Leopard', 'Bear', 'Wild boar'],
      languages: ['Hindi', 'Bengali', 'Tamil', 'Thai'],
      sample: '⚠️ हाथी उत्तरी बाड़ के पास आ रहा है!'
    },
    Americas: {
      animals: ['Bear', 'Wolf', 'Cougar', 'Jaguar', 'Coyote'],
      languages: ['Spanish', 'Portuguese', 'Quechua'],
      sample: '⚠️ Oso detectado cerca de la cerca norte!'
    },
    Europe: {
      animals: ['Wolf', 'Bear', 'Wild boar', 'Lynx', 'Fox'],
      languages: ['French', 'German', 'Italian', 'Polish'],
      sample: '⚠️ Loup détecté près de la clôture nord!'
    },
    Oceania: {
      animals: ['Crocodile', 'Dingo', 'Wild boar', 'Cassowary'],
      languages: ['English', 'Tok Pisin'],
      sample: '⚠️ Crocodile spotted near northern fence!'
    },
    MENA: {
      animals: ['Wolf', 'Hyena', 'Leopard', 'Wild boar'],
      languages: ['Arabic', 'Hebrew', 'Persian', 'Turkish'],
      sample: '⚠️ ذئب يقترب من السياج الشمالي!'
    }
  };
  
  const steps = [
    { icon: Camera, label: 'Camera Streams', desc: 'HLS, RTSP, IP cameras' },
    { icon: Zap, label: 'YOLO-World', desc: 'Real-time object detection' },
    { icon: Brain, label: 'Nova 2 Lite', desc: 'Threat analysis & scoring' },
    { icon: Network, label: 'Nova Embed', desc: 'Behavior pattern matching' },
    { icon: Radio, label: 'Alerts', desc: 'Multi-channel dispatch' }
  ];
  
  function setTheme(newTheme: string) {
    theme = newTheme;
    if (browser) {
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('paws-theme', newTheme);
    }
  }
  
  function goToDashboard() {
    if (browser) {
      window.location.href = '/dashboard';
    }
  }
  
  onMount(() => {
    const saved = localStorage.getItem('paws-theme') || 'dark';
    setTheme(saved);
    
    const interval = setInterval(() => {
      currentStep = (currentStep + 1) % steps.length;
    }, 2000);
    
    return () => clearInterval(interval);
  });
</script>

<svelte:head>
  <title>PAWS — Perimeter AI Wildlife Surveillance</title>
</svelte:head>

<div class="landing">
  <!-- Navigation -->
  <nav class="landing-nav">
    <div class="nav-content">
      <div class="brand">
        <Shield size={20} /> <span class="brand-text">PAWS v2.0</span>
      </div>
      
      <div class="nav-links">
        <a href="#pipeline" class="nav-link">How it works</a>
        <a href="#nova" class="nav-link">Live Demo</a>
        <button class="btn-enter" on:click={goToDashboard}>
          Enter Dashboard <ArrowRight size={16} />
        </button>
      </div>
    </div>
  </nav>
  
  <!-- Hero Section -->
  <section class="hero">
    <h1 class="hero-title">
      The world sleeps.<br>
      <span class="hero-highlight">PAWS doesn't.</span>
    </h1>
    
    <p class="hero-subtitle">
      AI-native wildlife intrusion detection. Any animal, any continent, any language. 
      Real-time alerts before the threat crosses your fence.
    </p>
    
    <div class="hero-actions">
      <button class="btn-primary" on:click={goToDashboard}>
        Launch Dashboard →
      </button>
      <button class="btn-secondary" on:click={() => {
        if (browser) document.getElementById('pipeline')?.scrollIntoView({ behavior: 'smooth' });
      }}>
        Watch Pipeline Demo
      </button>
    </div>
    
    <div class="hero-stats">
      <div class="stat">
        <div class="stat-value">750M+</div>
        <div class="stat-label">Smallholder<br>farmers</div>
      </div>
      <div class="stat">
        <div class="stat-value">&lt; 8s</div>
        <div class="stat-label">Detection to alert</div>
      </div>
      <div class="stat">
        <div class="stat-value">50+</div>
        <div class="stat-label">Languages<br>supported</div>
      </div>
    </div>
  </section>
  
  <!-- Pipeline Section -->
  <section id="pipeline" class="pipeline-section">
    <h2 class="section-title">Detection Pipeline</h2>
    <p class="section-subtitle">From camera frame to farmer alert in under 8 seconds</p>
    
    <div class="pipeline-grid">
      {#each steps as step, i}
        <div class="pipeline-card {i === currentStep ? 'active' : ''}">
          <div class="card-icon">
            <svelte:component this={step.icon} size={32} />
          </div>
          <div class="card-title">{step.label}</div>
          <div class="card-desc">{step.desc}</div>
        </div>
        {#if i < steps.length - 1}
          <div class="pipeline-arrow {i < currentStep ? 'active' : ''}">→</div>
        {/if}
      {/each}
    </div>
  </section>
  
  <!-- Nova Section -->
  <section id="nova" class="nova-section">
    <h2 class="section-title">Powered by Amazon Nova</h2>
    
    <div class="nova-grid">
      <div class="nova-card">
        <div class="nova-icon blue">🧠</div>
        <h3 class="nova-title">Nova 2 Lite Vision</h3>
        <p class="nova-desc">
          Analyzes every frame. Confirms threat, scores severity 1-10, 
          recommends deterrent, writes alerts in 6 languages at once.
        </p>
      </div>
      
      <div class="nova-card">
        <div class="nova-icon purple">🔗</div>
        <h3 class="nova-title">Nova Embeddings</h3>
        <p class="nova-desc">
          Behavior pattern matching. Compares to historical incidents. 
          384D embedding similarity search. Predicts escalation.
        </p>
      </div>
      
      <div class="nova-card">
        <div class="nova-icon amber">🔊</div>
        <h3 class="nova-title">Voice Alerts</h3>
        <p class="nova-desc">
          Farmer hears alert in their language. Hindi, Swahili, Spanish, Arabic. 
          Real-time speech synthesis powered by Polly.
        </p>
      </div>
    </div>
  </section>
  
  <!-- Global Coverage -->
  <section class="coverage-section">
    <div class="coverage-header">
      <span class="coverage-icon">🌍</span>
      <h2 class="section-title inline">Global Coverage</h2>
    </div>
    <p class="section-subtitle">Threat detection adapted to every region</p>
    
    <div class="region-tabs">
      {#each Object.keys(regions) as region}
        <button 
          class="region-tab {activeRegion === region ? 'active' : ''}"
          on:click={() => activeRegion = region}
        >
          {region}
        </button>
      {/each}
    </div>
    
    <div class="coverage-card">
      <div class="coverage-row">
        <span class="coverage-label">Animals detected:</span>
        <div class="tag-list">
          {#each regions[activeRegion].animals as animal}
            <span class="tag tag-amber">{animal}</span>
          {/each}
        </div>
      </div>
      
      <div class="coverage-row">
        <span class="coverage-label">Languages:</span>
        <div class="tag-list">
          {#each regions[activeRegion].languages as lang}
            <span class="tag tag-blue">{lang}</span>
          {/each}
        </div>
      </div>
      
      <div class="sample-alert">
        <span class="sample-label">Sample alert:</span>
        <div class="sample-text">{regions[activeRegion].sample}</div>
      </div>
    </div>
  </section>
  
  <!-- Footer CTA -->
  <section class="footer-cta">
    <h2 class="cta-title">Protecting farms. Preserving wildlife.</h2>
    <p class="cta-subtitle">Built for the Amazon Nova AI Hackathon.</p>
    
    <button class="btn-primary large" on:click={goToDashboard}>
      Launch Dashboard →
    </button>
    
    <div class="tech-badges">
      <span class="tech-badge">Amazon Nova</span>
      <span class="tech-badge">AWS Bedrock</span>
      <span class="tech-badge">Modal.com</span>
      <span class="tech-badge">ntfy.sh</span>
    </div>
  </section>
  
  <!-- Theme Switcher (Fixed Position) -->
  <div class="theme-switcher-fixed">
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
</div>

<style>
  .landing {
    min-height: 100vh;
    background: var(--bg-page);
    color: var(--text-primary);
  }
  
  /* Navigation */
  .landing-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--bg-card);
    border-bottom: 1px solid var(--bg-border);
  }
  
  .nav-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0.75rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .brand {
    font-size: 1.25rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .nav-links {
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  
  .nav-link {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.875rem;
    transition: color 0.2s;
  }
  
  .nav-link:hover {
    color: var(--text-primary);
  }
  
  .btn-enter {
    padding: 0.5rem 1rem;
    background: var(--green);
    border: none;
    border-radius: 0.375rem;
    color: #fff;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  .btn-enter:hover {
    opacity: 0.9;
  }
  
  /* Hero */
  .hero {
    max-width: 1000px;
    margin: 0 auto;
    padding: 5rem 1rem 4rem;
    text-align: center;
  }
  
  .hero-title {
    font-size: clamp(2.5rem, 7vw, 4.5rem);
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 1.5rem;
    letter-spacing: -0.02em;
  }
  
  .hero-highlight {
    color: var(--green);
  }
  
  .hero-subtitle {
    font-size: clamp(1rem, 2vw, 1.25rem);
    color: var(--text-secondary);
    line-height: 1.6;
    max-width: 700px;
    margin: 0 auto 2.5rem;
  }
  
  .hero-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 4rem;
    flex-wrap: wrap;
  }
  
  .btn-primary {
    padding: 0.75rem 2rem;
    background: var(--green);
    border: none;
    border-radius: 0.5rem;
    color: #fff;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  .btn-primary:hover {
    opacity: 0.9;
  }
  
  .btn-primary.large {
    padding: 0.875rem 2.5rem;
    font-size: 1.125rem;
  }
  
  .btn-secondary {
    padding: 0.75rem 2rem;
    background: transparent;
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .btn-secondary:hover {
    background: var(--bg-elevated);
  }
  
  .hero-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
    max-width: 600px;
    margin: 0 auto;
  }
  
  .stat {
    text-align: center;
  }
  
  .stat-value {
    font-size: clamp(2rem, 4vw, 3rem);
    font-weight: 900;
    color: var(--green);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.5rem;
  }
  
  .stat-label {
    font-size: 0.875rem;
    color: var(--text-muted);
    line-height: 1.3;
  }
  
  /* Pipeline Section */
  .pipeline-section {
    max-width: 1200px;
    margin: 0 auto;
    padding: 4rem 1rem;
    background: var(--bg-card);
    border-top: 1px solid var(--bg-border);
    border-bottom: 1px solid var(--bg-border);
  }
  
  .section-title {
    font-size: clamp(1.75rem, 4vw, 2.5rem);
    font-weight: 700;
    text-align: center;
    margin-bottom: 0.75rem;
  }
  
  .section-title.inline {
    display: inline;
    margin-left: 0.5rem;
  }
  
  .section-subtitle {
    text-align: center;
    color: var(--text-muted);
    font-size: 1rem;
    margin-bottom: 3rem;
  }
  
  .pipeline-grid {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
  }
  
  .pipeline-card {
    background: var(--bg-elevated);
    border: 2px solid var(--bg-border);
    border-radius: 0.75rem;
    padding: 1.5rem;
    width: 160px;
    text-align: center;
    transition: all 0.5s ease;
  }
  
  .pipeline-card.active {
    border-color: var(--green);
    background: rgba(34, 197, 94, 0.1);
    transform: scale(1.05);
    box-shadow: 0 10px 30px rgba(34, 197, 94, 0.2);
  }
  
  .card-icon {
    font-size: 2rem;
    margin-bottom: 0.75rem;
  }
  
  .card-title {
    font-weight: 600;
    font-size: 0.875rem;
    margin-bottom: 0.5rem;
  }
  
  .card-desc {
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  .pipeline-arrow {
    font-size: 1.5rem;
    color: var(--text-muted);
    opacity: 0.3;
    transition: all 0.5s;
  }
  
  .pipeline-arrow.active {
    color: var(--green);
    opacity: 1;
  }
  
  /* Nova Section */
  .nova-section {
    max-width: 1200px;
    margin: 0 auto;
    padding: 4rem 1rem;
  }
  
  .nova-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
  }
  
  .nova-card {
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    padding: 2rem;
    transition: all 0.3s;
  }
  
  .nova-card:hover {
    border-color: var(--green);
    transform: translateY(-4px);
  }
  
  .nova-icon {
    width: 3rem;
    height: 3rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }
  
  .nova-icon.blue {
    background: rgba(59, 130, 246, 0.1);
  }
  
  .nova-icon.purple {
    background: rgba(147, 51, 234, 0.1);
  }
  
  .nova-icon.amber {
    background: rgba(245, 158, 11, 0.1);
  }
  
  .nova-title {
    font-size: 1.125rem;
    font-weight: 700;
    margin-bottom: 0.75rem;
  }
  
  .nova-desc {
    font-size: 0.875rem;
    color: var(--text-secondary);
    line-height: 1.6;
  }
  
  /* Coverage Section */
  .coverage-section {
    max-width: 1000px;
    margin: 0 auto;
    padding: 4rem 1rem;
    background: var(--bg-card);
    border-top: 1px solid var(--bg-border);
    border-bottom: 1px solid var(--bg-border);
  }
  
  .coverage-header {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 0.75rem;
  }
  
  .coverage-icon {
    font-size: 2rem;
  }
  
  .region-tabs {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }
  
  .region-tab {
    padding: 0.5rem 1rem;
    background: var(--bg-elevated);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .region-tab:hover {
    color: var(--text-primary);
  }
  
  .region-tab.active {
    background: var(--green);
    border-color: var(--green);
    color: #fff;
  }
  
  .coverage-card {
    background: var(--bg-elevated);
    border: 1px solid var(--bg-border);
    border-radius: 0.75rem;
    padding: 1.5rem;
    max-width: 700px;
    margin: 0 auto;
  }
  
  .coverage-row {
    margin-bottom: 1.25rem;
  }
  
  .coverage-row:last-child {
    margin-bottom: 0;
  }
  
  .coverage-label {
    display: block;
    font-size: 0.875rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }
  
  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .tag {
    padding: 0.375rem 0.75rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
  }
  
  .tag-amber {
    background: var(--amber-bg);
    color: var(--amber);
  }
  
  .tag-blue {
    background: var(--blue-bg);
    color: var(--blue);
  }
  
  .sample-alert {
    background: var(--bg-page);
    border: 1px solid var(--bg-border);
    border-radius: 0.5rem;
    padding: 1rem;
  }
  
  .sample-label {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
  }
  
  .sample-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.875rem;
  }
  
  /* Footer CTA */
  .footer-cta {
    max-width: 800px;
    margin: 0 auto;
    padding: 4rem 1rem;
    text-align: center;
  }
  
  .cta-title {
    font-size: clamp(1.5rem, 4vw, 2rem);
    font-weight: 700;
    margin-bottom: 0.75rem;
  }
  
  .cta-subtitle {
    color: var(--text-muted);
    margin-bottom: 2rem;
  }
  
  .tech-badges {
    display: flex;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 2rem;
  }
  
  .tech-badge {
    padding: 0.5rem 1rem;
    background: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: 0.375rem;
    font-size: 0.75rem;
    color: var(--text-muted);
  }
  
  /* Theme Switcher Fixed */
  .theme-switcher-fixed {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    display: flex;
    gap: 0.5rem;
    background: var(--bg-card);
    padding: 0.5rem;
    border-radius: 0.5rem;
    border: 1px solid var(--bg-border);
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    z-index: 1000;
  }
  
  .theme-btn {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 0.375rem;
    border: 1px solid var(--bg-border);
    background: transparent;
    font-size: 1.25rem;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .theme-btn:hover {
    border-color: var(--green);
  }
  
  .theme-btn.active {
    border-color: var(--green);
    background: var(--green-bg);
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
  }
  
  @media (max-width: 768px) {
    .nav-link {
      display: none;
    }
    
    .hero {
      padding: 3rem 1rem 2rem;
    }
    
    .pipeline-arrow {
      display: none;
    }
    
    .theme-switcher-fixed {
      bottom: 1rem;
      right: 1rem;
    }
  }
</style>
