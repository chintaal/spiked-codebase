<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { smoothTranscriptionService } from '$lib/services/smoothTranscription.js';
  
  // Component props
  export let showVolumeBar = true;
  export let showTimestamp = true;
  export let autoScroll = true;
  export let maxTranscripts = 50;
  export let animationDuration = 300;
  
  // Component state
  let isInitialized = false;
  let isListening = false;
  let isSpeaking = false;
  let volumeLevel = 0;
  let currentStatus = 'ready';
  let interimText = '';
  let finalTranscripts = [];
  let errorMessage = null;
  
  // UI references
  let transcriptContainer;
  let interimElement;
  let volumeBarElement;
  
  // Animation state
  let pulseAnimation = false;
  let volumeAnimation = false;
  let textAnimation = false;
  let lastVolumeUpdate = 0;
  
  onMount(async () => {
    try {
      console.log('Initializing Smooth Live Transcription...');
      
      // Initialize the transcription service
      await smoothTranscriptionService.initialize();
      
      // Set up event callbacks
      smoothTranscriptionService.setCallbacks({
        onTranscriptUpdate: handleTranscriptUpdate,
        onInterimUpdate: handleInterimUpdate,
        onVolumeUpdate: handleVolumeUpdate,
        onStatusChange: handleStatusChange,
        onError: handleError
      });
      
      isInitialized = true;
      console.log('Smooth Live Transcription initialized');
      
    } catch (error) {
      console.error('Failed to initialize transcription:', error);
      errorMessage = `Initialization failed: ${error.message}`;
    }
  });
  
  onDestroy(() => {
    if (smoothTranscriptionService) {
      smoothTranscriptionService.cleanup();
    }
  });
  
  /**
   * Handle transcript updates (final results)
   */
  async function handleTranscriptUpdate(transcript) {
    // Add to transcripts list
    finalTranscripts = [...finalTranscripts, transcript];
    
    // Limit transcript history
    if (finalTranscripts.length > maxTranscripts) {
      finalTranscripts = finalTranscripts.slice(-maxTranscripts);
    }
    
    // Clear interim text when final result comes in
    interimText = '';
    
    // Trigger text animation
    textAnimation = true;
    setTimeout(() => textAnimation = false, animationDuration);
    
    // Auto-scroll to bottom
    if (autoScroll && transcriptContainer) {
      await tick();
      transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
    }
  }
  
  /**
   * Handle interim updates (live typing effect)
   */
  function handleInterimUpdate(text) {
    interimText = text;
    
    // Animate interim text
    if (interimElement) {
      interimElement.style.opacity = '0.7';
      setTimeout(() => {
        if (interimElement) {
          interimElement.style.opacity = '1';
        }
      }, 50);
    }
  }
  
  /**
   * Handle volume updates for visual feedback
   */
  function handleVolumeUpdate(level) {
    volumeLevel = level;
    
    // Throttle volume updates for smooth animation
    const now = Date.now();
    if (now - lastVolumeUpdate > 50) {
      lastVolumeUpdate = now;
      
      // Update volume bar
      if (volumeBarElement) {
        const percentage = Math.min(level * 100, 100);
        volumeBarElement.style.width = `${percentage}%`;
        
        // Add pulse effect for high volume
        if (level > 0.3) {
          volumeAnimation = true;
          setTimeout(() => volumeAnimation = false, 100);
        }
      }
    }
    
    // Update speaking state
    const wasSpeaking = isSpeaking;
    isSpeaking = level > 0.01;
    
    // Trigger pulse animation when speaking starts
    if (isSpeaking && !wasSpeaking) {
      pulseAnimation = true;
      setTimeout(() => pulseAnimation = false, 1000);
    }
  }
  
  /**
   * Handle status changes
   */
  function handleStatusChange(status) {
    currentStatus = status;
    console.log('Status changed:', status);
  }
  
  /**
   * Handle errors
   */
  function handleError(error) {
    console.error('Transcription error:', error);
    errorMessage = error;
    
    // Clear error after 5 seconds
    setTimeout(() => {
      errorMessage = null;
    }, 5000);
  }
  
  /**
   * Start transcription
   */
  async function startTranscription() {
    if (!isInitialized) {
      errorMessage = 'Service not initialized';
      return;
    }
    
    try {
      await smoothTranscriptionService.startTranscription();
      isListening = true;
    } catch (error) {
      console.error('Failed to start transcription:', error);
      errorMessage = `Failed to start: ${error.message}`;
    }
  }
  
  /**
   * Stop transcription
   */
  function stopTranscription() {
    smoothTranscriptionService.stopTranscription();
    isListening = false;
    isSpeaking = false;
    volumeLevel = 0;
    interimText = '';
  }
  
  /**
   * Clear transcripts
   */
  function clearTranscripts() {
    finalTranscripts = [];
    interimText = '';
  }
</script>

<div class="smooth-transcription">
  <!-- Header with controls -->
  <div class="header">
    <div class="title-section">
      <h2 class="title">
        🎤 Live Transcription
        {#if isListening}
          <span class="status-indicator listening" class:pulse={pulseAnimation}>●</span>
        {:else}
          <span class="status-indicator ready">●</span>
        {/if}
      </h2>
      <p class="subtitle">Real-time speech-to-text conversion</p>
    </div>
    
    <div class="controls">
      {#if !isListening}
        <button 
          class="btn btn-primary"
          on:click={startTranscription}
          disabled={!isInitialized}
        >
          <span class="icon">🎤</span>
          Start Listening
        </button>
      {:else}
        <button 
          class="btn btn-danger"
          on:click={stopTranscription}
        >
          <span class="icon">⏹️</span>
          Stop
        </button>
      {/if}
      
      <button 
        class="btn btn-secondary"
        on:click={clearTranscripts}
        disabled={finalTranscripts.length === 0}
      >
        <span class="icon">🗑️</span>
        Clear
      </button>
    </div>
  </div>
  
  <!-- Volume bar -->
  {#if showVolumeBar && isListening}
    <div class="volume-container">
      <div class="volume-label">
        <span class="icon">🔊</span>
        Volume
      </div>
      <div class="volume-bar-container" class:active={isSpeaking}>
        <div 
          class="volume-bar" 
          class:pulse={volumeAnimation}
          bind:this={volumeBarElement}
        ></div>
      </div>
      <div class="volume-level">
        {Math.round(volumeLevel * 100)}%
      </div>
    </div>
  {/if}
  
  <!-- Error message -->
  {#if errorMessage}
    <div class="error-message">
      <span class="error-icon">⚠️</span>
      {errorMessage}
    </div>
  {/if}
  
  <!-- Live transcription display -->
  <div class="transcription-container" bind:this={transcriptContainer}>
    {#if finalTranscripts.length === 0 && !interimText}
      <div class="empty-state">
        <div class="empty-icon">🎙️</div>
        <p class="empty-text">
          {#if !isListening}
            Click "Start Listening" to begin transcription
          {:else}
            Listening... Start speaking to see live transcription
          {/if}
        </p>
      </div>
    {:else}
      <!-- Final transcripts -->
      {#each finalTranscripts as transcript (transcript.id)}
        <div 
          class="transcript-entry" 
          class:animate={textAnimation}
        >
          {#if showTimestamp}
            <span class="timestamp">{transcript.timestamp}</span>
          {/if}
          <span class="speaker">{transcript.speaker}:</span>
          <span class="text">{transcript.text}</span>
        </div>
      {/each}
      
      <!-- Interim transcript (live typing) -->
      {#if interimText}
        <div 
          class="interim-transcript"
          bind:this={interimElement}
        >
          <span class="interim-indicator">
            <span class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </span>
          </span>
          <span class="interim-text">{interimText}</span>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .smooth-transcription {
    width: 100%;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    gap: 20px;
  }
  
  .title-section {
    flex: 1;
  }
  
  .title {
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 5px 0;
    color: #1f2937;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .status-indicator {
    font-size: 0.8rem;
    transition: all 0.3s ease;
  }
  
  .status-indicator.listening {
    color: #ef4444;
    animation: pulse 2s infinite;
  }
  
  .status-indicator.ready {
    color: #6b7280;
  }
  
  .status-indicator.pulse {
    animation: pulse 0.5s ease-in-out;
  }
  
  .subtitle {
    color: #6b7280;
    margin: 0;
    font-size: 0.9rem;
  }
  
  .controls {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  
  .btn {
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
  }
  
  .btn-primary {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
  }
  
  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
  }
  
  .btn-danger {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
  }
  
  .btn-danger:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
  }
  
  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
  }
  
  .btn-secondary:hover:not(:disabled) {
    background: #e5e7eb;
  }
  
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
  }
  
  .icon {
    font-size: 1em;
  }
  
  .volume-container {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 20px;
    padding: 15px;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 12px;
    border: 1px solid #e2e8f0;
  }
  
  .volume-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    color: #374151;
    font-size: 0.9rem;
    min-width: 80px;
  }
  
  .volume-bar-container {
    flex: 1;
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    overflow: hidden;
    position: relative;
    transition: all 0.3s ease;
  }
  
  .volume-bar-container.active {
    background: #dbeafe;
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
  }
  
  .volume-bar {
    height: 100%;
    background: linear-gradient(90deg, #10b981 0%, #3b82f6 50%, #ef4444 100%);
    border-radius: 3px;
    transition: width 0.1s ease;
    width: 0%;
  }
  
  .volume-bar.pulse {
    animation: volumePulse 0.3s ease-in-out;
  }
  
  .volume-level {
    font-weight: 600;
    color: #374151;
    font-size: 0.8rem;
    min-width: 40px;
    text-align: right;
  }
  
  .error-message {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #dc2626;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
  }
  
  .error-icon {
    font-size: 1.2rem;
  }
  
  .transcription-container {
    min-height: 300px;
    max-height: 500px;
    overflow-y: auto;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px;
    scroll-behavior: smooth;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: #6b7280;
  }
  
  .empty-icon {
    font-size: 3rem;
    margin-bottom: 15px;
    opacity: 0.5;
  }
  
  .empty-text {
    font-size: 1rem;
    text-align: center;
    margin: 0;
  }
  
  .transcript-entry {
    margin-bottom: 15px;
    padding: 12px 16px;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 4px solid #3b82f6;
    transition: all 0.3s ease;
  }
  
  .transcript-entry.animate {
    animation: slideIn 0.3s ease-out;
  }
  
  .timestamp {
    color: #6b7280;
    font-size: 0.8rem;
    font-weight: 500;
    margin-right: 10px;
  }
  
  .speaker {
    font-weight: 600;
    color: #374151;
    margin-right: 8px;
  }
  
  .text {
    color: #1f2937;
    line-height: 1.5;
  }
  
  .interim-transcript {
    margin-top: 15px;
    padding: 12px 16px;
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border-radius: 8px;
    border-left: 4px solid #60a5fa;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.2s ease;
  }
  
  .interim-indicator {
    display: flex;
    align-items: center;
  }
  
  .typing-dots {
    display: flex;
    gap: 3px;
  }
  
  .typing-dots span {
    width: 4px;
    height: 4px;
    background: #3b82f6;
    border-radius: 50%;
    animation: typingDots 1.4s infinite ease-in-out;
  }
  
  .typing-dots span:nth-child(1) {
    animation-delay: -0.32s;
  }
  
  .typing-dots span:nth-child(2) {
    animation-delay: -0.16s;
  }
  
  .interim-text {
    color: #1e40af;
    font-style: italic;
    opacity: 0.8;
    flex: 1;
  }
  
  /* Animations */
  @keyframes pulse {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.5;
      transform: scale(1.1);
    }
  }
  
  @keyframes volumePulse {
    0% {
      transform: scaleY(1);
    }
    50% {
      transform: scaleY(1.2);
    }
    100% {
      transform: scaleY(1);
    }
  }
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  @keyframes typingDots {
    0%, 80%, 100% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
  
  /* Responsive design */
  @media (max-width: 640px) {
    .smooth-transcription {
      padding: 15px;
    }
    
    .header {
      flex-direction: column;
      align-items: stretch;
      gap: 15px;
    }
    
    .controls {
      justify-content: center;
    }
    
    .volume-container {
      flex-direction: column;
      gap: 10px;
    }
    
    .volume-bar-container {
      order: 1;
    }
    
    .volume-label,
    .volume-level {
      justify-content: center;
      text-align: center;
    }
    
    .transcription-container {
      max-height: 400px;
    }
  }
</style>
