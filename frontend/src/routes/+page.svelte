<script>
  import { onMount } from 'svelte';
  
  let backendStatus = 'Checking...';
  
  onMount(async () => {
    try {
      const response = await fetch('http://localhost:8000/');
      const data = await response.json();
      backendStatus = data.message || 'Running';
    } catch (error) {
      backendStatus = 'Not available - please start the backend server';
      console.error('Backend connection error:', error);
    }
  });
</script>

<svelte:head>
  <title>Sales Assistant API Demo</title>
  <meta name="description" content="Demo interface for Sales Assistant APIs" />
</svelte:head>

<main>
  <h1>Sales Assistant API Demo</h1>
  <p>Backend status: <span class={backendStatus.includes('Not') ? 'error' : 'success'}>{backendStatus}</span></p>

  <nav>
    <ul>
      <li><a href="/action-items">Action Items Extraction</a></li>
      <li><a href="/search">Knowledge Search</a></li>
      <li><a href="/store">Store Transcripts</a></li>
      <li><a href="/transcribe">Real-time Transcription</a></li>
      <li><a href="/smart-transcribe">Smart Transcription with LLM</a></li>
      <li><a href="/live-transcribe" class="featured">Live Transcription</a></li>
      <li><a href="/sentiment">Sentiment Analysis</a></li>
      <li><a href="/cache" class="featured">Cache Management</a></li>
      <li><a href="/files">File Management</a></li>
    </ul>
  </nav>
  
  <div class="info-box">
    <h2>Available APIs</h2>
    <ul>
      <li><strong>Action Items API</strong> - Extract action items from meeting transcripts</li>
      <li><strong>Search API</strong> - Search for information in your knowledge base</li>
      <li><strong>Store API</strong> - Store transcripts in vector database</li>
      <li><strong>Real-time Transcription</strong> - Live audio transcription via WebSocket</li>
      <li><strong>Smart Transcription</strong> - Incremental transcription with LLM formatting</li>
      <li><strong>Live Transcription</strong> - Instant speech-to-text with real-time display</li>
      <li><strong>Sentiment Analysis</strong> - Analyze the sentiment of conversation</li>
      <li><strong>Cache Management</strong> - Manage HealthAssist answer cache for zero-latency responses</li>
      <li><strong>File Management</strong> - Upload and manage knowledge base documents</li>
    </ul>
  </div>
</main>

<style>
  main {
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem;
  }
  
  h1 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    color: #1d3557;
  }
  
  .success {
    color: #2ecc71;
    font-weight: bold;
  }
  
  .error {
    color: #e74c3c;
    font-weight: bold;
  }
  
  nav {
    margin: 2rem 0;
  }
  
  nav ul {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 0;
    list-style: none;
  }
  
  nav a {
    display: block;
    padding: 0.75rem 1.5rem;
    background-color: #457b9d;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    transition: background-color 0.2s;
  }
  
  nav a:hover {
    background-color: #1d3557;
  }
  
  nav a.featured {
    background-color: #2a9d8f;
    position: relative;
    overflow: hidden;
  }
  
  nav a.featured::after {
    content: "New!";
    position: absolute;
    top: -8px;
    right: -18px;
    background: #e63946;
    color: white;
    font-size: 0.6rem;
    padding: 2px 15px;
    transform: rotate(45deg);
    font-weight: bold;
  }
  
  nav a.featured:hover {
    background-color: #1e7b72;
  }
  
  .info-box {
    margin-top: 2rem;
    padding: 1.5rem;
    background-color: #f1faee;
    border-radius: 8px;
  }
  
  .info-box h2 {
    margin-top: 0;
    color: #1d3557;
  }
  
  .info-box ul {
    padding-left: 1.5rem;
  }
  
  .info-box li {
    margin-bottom: 0.5rem;
  }
</style>
