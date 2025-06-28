<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
  import { enhancedTranscriptionService } from '$lib/services/enhancedTranscription.js';
  import { transcriptionStore } from '$lib/stores/transcription.js';
  import { darkMode } from '$lib/stores/ui.js';
  
  const dispatch = createEventDispatcher();
  
  // Component props
  export let mode = 'hybrid'; // 'webspeech' | 'whisper' | 'hybrid'
  export let autoStart = false;
  export let showVolumeBar = true;
  export let showLiveText = true;
  export let showTimestamp = true;
  export let animationEnabled = true;
  
  // Component state
  let isInitialized = false;
  let currentStatus = 'ready';
  let currentVolume = 0;
  let liveText = '';
  let finalText = '';
  let errorMessage = null;
  let isRecording = false;
  
  // UI references
  let transcriptionContainer;
  let liveTextElement;
  let volumeBarElement;
  
  // Animation state
  let pulseAnimation = false;
  let volumeAnimation = false;
  let textAnimation = false;
  
  // Configuration
  const config = {
    showVolume: showVolumeBar,
    showInterim: showLiveText,
    autoScroll: true,
    language: 'en-US',
    continuous: true,
    interimResults: true
  };
  
  // Subscribe to transcription store
  const unsubscribe = transcriptionStore.subscribe(state => {
    currentStatus = state.status;
    currentVolume = state.volumeLevel;
    liveText = state.liveText;
    finalText = state.finalText;
    errorMessage = state.errorMessage;
    isRecording = state.isRecording;
    
    // Trigger animations based on state changes
    if (animationEnabled) {
      handleStateChange(state);
    }
  });
  
  onMount(async () => {
    try {
      // Initialize enhanced transcription service
      await enhancedTranscriptionService.initialize(mode, config);
      isInitialized = true;
      
      // Auto-start if enabled
      if (autoStart) {
        await startTranscription();
      }
      
      console.log('Enhanced Transcription Component mounted');
      
    } catch (error) {
      console.error('Failed to initialize transcription component:', error);
      errorMessage = `Initialization failed: ${error.message}`;
    }
  });
  
  onDestroy(() => {
    // Cleanup subscriptions
    if (unsubscribe) {
      unsubscribe();
    }
    
    // Cleanup service
    if (enhancedTranscriptionService) {
      enhancedTranscriptionService.cleanup();
    }
  });
  
  /**
   * Handle state changes for animations
   */
  function handleStateChange(state) {
    // Volume animation
    if (state.volumeLevel > 10 && state.isRecording) {
      volumeAnimation = true;
      setTimeout(() => volumeAnimation = false, 100);
    }
    
    // Text animation when new content arrives
    if (state.liveText !== liveText || state.finalText !== finalText) {
      textAnimation = true;
      setTimeout(() => textAnimation = false, 300);
    }
    
    // Pulse animation when recording starts/stops
    if (state.isRecording !== isRecording) {
      pulseAnimation = true;
      setTimeout(() => pulseAnimation = false, 500);
    }
  }
  
  /**
   * Start transcription
   */
  async function startTranscription() {
    try {
      if (!isInitialized) {
        throw new Error('Service not initialized');
      }
      
      await enhancedTranscriptionService.startTranscription();
      
      // Dispatch event
      dispatch('transcriptionStarted', {
        method: mode,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Failed to start transcription:', error);
      dispatch('transcriptionError', {
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * Stop transcription
   */
  async function stopTranscription() {
    try {
      await enhancedTranscriptionService.stopTranscription();
      
      // Dispatch event with final text
      dispatch('transcriptionStopped', {
        finalText: finalText,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Failed to stop transcription:', error);
      dispatch('transcriptionError', {
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * Toggle transcription
   */
  async function toggleTranscription() {
    if (isRecording) {
      await stopTranscription();
    } else {
      await startTranscription();
    }
  }
  
  /**
   * Clear transcription
   */
  function clearTranscription() {
    enhancedTranscriptionService.clearBuffers();
    dispatch('transcriptionCleared');
  }
  
  /**
   * Get status color for UI
   */
  function getStatusColor(status) {
    switch (status) {
      case 'ready': return 'text-green-500';
      case 'listening': return 'text-blue-500';
      case 'recording': return 'text-red-500';
      case 'transcribing': return 'text-yellow-500';
      case 'error': return 'text-red-600';
      case 'connecting': return 'text-orange-500';
      case 'reconnecting': return 'text-orange-600';
      default: return 'text-gray-500';
    }
  }
  
  /**
   * Get volume bar width
   */
  function getVolumeWidth(volume) {
    return Math.min(100, Math.max(0, volume));
  }
  
  /**
   * Format timestamp
   */
  function formatTimestamp() {
    return new Date().toLocaleTimeString();
  }
  
  /**
   * Auto-scroll to bottom
   */
  async function autoScroll() {
    if (transcriptionContainer && config.autoScroll) {
      await tick();
      transcriptionContainer.scrollTop = transcriptionContainer.scrollHeight;
    }
  }
  
  // Auto-scroll when content changes
  $: if (liveText || finalText) {
    autoScroll();
  }
</script>

<div class="enhanced-transcription-container" class:dark={$darkMode}>
  <!-- Header with controls -->
  <div class="transcription-header">
    <div class="status-section">
      <div class="status-indicator {getStatusColor(currentStatus)}" 
           class:pulse={pulseAnimation}>
        <div class="status-dot"></div>
        <span class="status-text">{currentStatus}</span>
      </div>
      
      {#if showTimestamp}
        <div class="timestamp">
          {formatTimestamp()}
        </div>
      {/if}
    </div>
    
    <div class="controls-section">
      <button 
        class="control-button"
        class:recording={isRecording}
        class:pulse={pulseAnimation}
        on:click={toggleTranscription}
        disabled={!isInitialized}
        title={isRecording ? 'Stop Recording' : 'Start Recording'}
      >
        {#if isRecording}
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
          </svg>
        {:else}
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" />
          </svg>
        {/if}
      </button>
      
      <button 
        class="control-button secondary"
        on:click={clearTranscription}
        title="Clear Transcription"
        aria-label="Clear Transcription"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1-1H8a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  </div>
  
  <!-- Volume Bar -->
  {#if showVolumeBar && isRecording}
    <div class="volume-bar-container">
      <div class="volume-bar-background">
        <div 
          class="volume-bar-fill"
          class:volume-animation={volumeAnimation}
          style="width: {getVolumeWidth(currentVolume)}%"
          bind:this={volumeBarElement}
        ></div>
      </div>
      <span class="volume-text">{Math.round(currentVolume)}%</span>
    </div>
  {/if}
  
  <!-- Error Display -->
  {#if errorMessage}
    <div class="error-container">
      <div class="error-icon">⚠️</div>
      <div class="error-text">{errorMessage}</div>
      <button 
        class="error-dismiss"
        on:click={() => transcriptionStore.setError(null)}
      >
        ✕
      </button>
    </div>
  {/if}
  
  <!-- Transcription Display -->
  <div 
    class="transcription-display"
    bind:this={transcriptionContainer}
  >
    <!-- Final Text -->
    {#if finalText}
      <div class="final-text" class:text-animation={textAnimation}>
        {finalText}
      </div>
    {/if}
    
    <!-- Live Text -->
    {#if showLiveText && liveText && isRecording}
      <div 
        class="live-text"
        class:text-animation={textAnimation}
        bind:this={liveTextElement}
      >
        <span class="live-indicator">🎤</span>
        <span class="live-content">{liveText}</span>
        <span class="cursor-blink">|</span>
      </div>
    {/if}
    
    <!-- Listening Indicator -->
    {#if isRecording && !liveText && !finalText}
      <div class="listening-indicator">
        <div class="listening-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <span class="listening-text">Listening...</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .enhanced-transcription-container {
    width: 100%;
    max-width: 64rem;
    margin: 0 auto;
    background-color: white;
    border-radius: 0.5rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    border: 1px solid #e5e7eb;
    transition: all 0.3s ease;
  }
  
  .enhanced-transcription-container.dark {
    background-color: #1f2937;
    border-color: #374151;
  }
  
  /* Header */
  .transcription-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e5e7eb;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  }
  
  .dark .transcription-header {
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
    border-bottom-color: #374151;
  }
  
  .status-section {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }
  
  .status-indicator.pulse {
    animation: pulse 0.5s ease-in-out;
  }
  
  .status-dot {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 50%;
    background: currentColor;
  }
  
  .status-text {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: capitalize;
  }
  
  .timestamp {
    font-size: 0.75rem;
    color: #6b7280;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  
  .controls-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .control-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 3rem;
    height: 3rem;
    border-radius: 50%;
    border: 2px solid #d1d5db;
    transition: all 0.3s ease;
    background-color: white;
    color: #4b5563;
    cursor: pointer;
  }
  
  .control-button:hover {
    background-color: #f9fafb;
    transform: scale(1.05);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  
  .control-button.recording {
    background-color: #ef4444;
    border-color: #ef4444;
    color: white;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
  }
  
  .control-button.recording:hover {
    background-color: #dc2626;
  }
  
  .control-button.pulse {
    animation: pulse 0.5s ease-in-out;
  }
  
  .control-button.secondary {
    width: 2.5rem;
    height: 2.5rem;
    background-color: #f3f4f6;
    color: #6b7280;
  }
  
  .control-button.secondary:hover {
    background-color: #e5e7eb;
  }
  
  .dark .control-button {
    background-color: #374151;
    border-color: #4b5563;
    color: #d1d5db;
  }
  
  .dark .control-button:hover {
    background-color: #4b5563;
  }
  
  .dark .control-button.secondary {
    background-color: #1f2937;
    color: #9ca3af;
  }
  
  .dark .control-button.secondary:hover {
    background-color: #374151;
  }
  
  /* Volume Bar */
  .volume-bar-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 1rem;
    background-color: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }
  
  .dark .volume-bar-container {
    background-color: #111827;
    border-bottom-color: #374151;
  }
  
  .volume-bar-background {
    flex: 1;
    height: 0.5rem;
    background-color: #e5e7eb;
    border-radius: 9999px;
    overflow: hidden;
  }
  
  .dark .volume-bar-background {
    background-color: #374151;
  }
  
  .volume-bar-fill {
    height: 100%;
    border-radius: 9999px;
    transition: all 0.1s ease;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #fbbf24 80%, #ef4444 100%);
  }
  
  .volume-bar-fill.volume-animation {
    animation: volumePulse 0.1s ease-out;
  }
  
  .volume-text {
    font-size: 0.75rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
    color: #6b7280;
    min-width: 3rem;
    text-align: right;
  }
  
  /* Error Display */
  .error-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    margin: 1rem;
    margin-bottom: 0;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 0.5rem;
  }
  
  .dark .error-container {
    background-color: rgba(127, 29, 29, 0.2);
    border-color: #991b1b;
  }
  
  .error-icon {
    color: #ef4444;
    font-size: 1.125rem;
  }
  
  .error-text {
    flex: 1;
    font-size: 0.875rem;
    color: #b91c1c;
  }
  
  .dark .error-text {
    color: #fca5a5;
  }
  
  .error-dismiss {
    color: #ef4444;
    background: none;
    border: none;
    cursor: pointer;
    transition: color 0.2s ease;
  }
  
  .error-dismiss:hover {
    color: #b91c1c;
  }
  
  /* Transcription Display */
  .transcription-display {
    padding: 1.5rem;
    min-height: 12.5rem;
    max-height: 25rem;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
  }
  
  .transcription-display::-webkit-scrollbar {
    width: 0.5rem;
  }
  
  .transcription-display::-webkit-scrollbar-track {
    background: transparent;
  }
  
  .transcription-display::-webkit-scrollbar-thumb {
    background-color: #d1d5db;
    border-radius: 9999px;
  }
  
  .dark .transcription-display::-webkit-scrollbar-thumb {
    background-color: #4b5563;
  }
  
  .final-text {
    color: #1f2937;
    line-height: 1.7;
    margin-bottom: 1rem;
    font-size: 1.1rem;
  }
  
  .dark .final-text {
    color: #e5e7eb;
  }
  
  .final-text.text-animation {
    animation: textFadeIn 0.3s ease-out;
  }
  
  .live-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem;
    background-color: #dbeafe;
    border: 1px solid #bfdbfe;
    border-radius: 0.5rem;
    transition: all 0.3s ease;
  }
  
  .dark .live-text {
    background-color: rgba(30, 64, 175, 0.2);
    border-color: #1e40af;
  }
  
  .live-text.text-animation {
    animation: liveTextPulse 0.3s ease-out;
  }
  
  .live-indicator {
    color: #3b82f6;
    font-size: 1.125rem;
  }
  
  .live-content {
    flex: 1;
    color: #1e40af;
    font-weight: 500;
  }
  
  .dark .live-content {
    color: #93c5fd;
  }
  
  .cursor-blink {
    color: #3b82f6;
    animation: blink 1s infinite;
  }
  
  /* Listening Indicator */
  .listening-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 2rem 0;
    color: #6b7280;
  }
  
  .listening-dots {
    display: flex;
    gap: 0.25rem;
  }
  
  .dot {
    width: 0.5rem;
    height: 0.5rem;
    background-color: #9ca3af;
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite both;
  }
  
  .dot:nth-child(1) { animation-delay: -0.32s; }
  .dot:nth-child(2) { animation-delay: -0.16s; }
  .dot:nth-child(3) { animation-delay: 0s; }
  
  .listening-text {
    font-size: 0.875rem;
    font-weight: 500;
  }
  
  /* Icon sizes */
  .w-5 { width: 1.25rem; }
  .h-5 { height: 1.25rem; }
  .w-6 { width: 1.5rem; }
  .h-6 { height: 1.5rem; }
  
  /* Animations */
  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }
  
  @keyframes volumePulse {
    0% { transform: scaleY(1); }
    50% { transform: scaleY(1.2); }
    100% { transform: scaleY(1); }
  }
  
  @keyframes textFadeIn {
    0% { opacity: 0; transform: translateY(10px); }
    100% { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes liveTextPulse {
    0% { background-color: #dbeafe; }
    50% { background-color: #93c5fd; }
    100% { background-color: #dbeafe; }
  }
  
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
  
  @keyframes bounce {
    0%, 80%, 100% {
      transform: scale(0);
    }
    40% {
      transform: scale(1);
    }
  }
  
  /* Dark mode overrides */
  .dark .listening-indicator {
    color: #9ca3af;
  }
  
  .dark .dot {
    background-color: #6b7280;
  }
  
  /* Responsive design */
  @media (max-width: 640px) {
    .transcription-header {
      flex-direction: column;
      gap: 0.75rem;
    }
    
    .status-section,
    .controls-section {
      width: 100%;
      justify-content: center;
    }
    
    .transcription-display {
      padding: 1rem;
    }
    
    .volume-bar-container {
      padding: 0.5rem 1rem;
    }
  }
</style>
