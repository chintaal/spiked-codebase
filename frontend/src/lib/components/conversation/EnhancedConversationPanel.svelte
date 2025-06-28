<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
  import { enhancedTranscriptionService } from '$lib/services/enhancedTranscription.js';
  import { transcriptionStore } from '$lib/stores/transcription.js';
  import { detectQuestion, extractQuestions } from '$lib/utils/questionDetector.js';
  import { darkMode } from '$lib/stores/ui.js';
  
  const dispatch = createEventDispatcher();
  
  // Enhanced transcription settings
  export let transcriptionMethod = 'hybrid'; // 'webspeech' | 'whisper' | 'hybrid'
  export let showVolumeBar = true;
  export let animationsEnabled = true;
  export let autoSendEnabled = false;
  export let wordsThreshold = 15;
  export let timeThreshold = 10; // seconds
  
  // Component state
  let isInitialized = false;
  let currentStatus = 'ready';
  let currentVolume = 0;
  let liveText = '';
  let finalText = '';
  let errorMessage = null;
  let isRecording = false;
  let isConnected = false;
  
  // UI references
  let conversationHistoryEl;
  let autoScroll = true;
  
  // Animation state
  let pulseAnimation = false;
  let volumeAnimation = false;
  let textAnimation = false;
  
  // Auto-send functionality
  let accumulatedTranscription = '';
  let lastDispatchTime = Date.now();
  
  // Subscribe to transcription store
  const unsubscribe = transcriptionStore.subscribe(state => {
    currentStatus = state.status;
    currentVolume = state.volumeLevel;
    liveText = state.liveText;
    finalText = state.finalText;
    errorMessage = state.errorMessage;
    isRecording = state.isRecording;
    isConnected = state.isConnected;
    
    // Handle animations
    if (animationsEnabled) {
      handleStateChange(state);
    }
    
    // Handle auto-send functionality
    if (autoSendEnabled && state.finalText) {
      handleAutoSend(state.finalText);
    }
  });
  
  onMount(async () => {
    try {
      console.log('Initializing Enhanced Conversation Panel');
      
      // Initialize enhanced transcription service
      await enhancedTranscriptionService.initialize(transcriptionMethod, {
        showVolume: showVolumeBar,
        showInterim: true,
        autoScroll: true,
        language: 'en-US',
        continuous: true,
        interimResults: true
      });
      
      isInitialized = true;
      console.log('Enhanced Conversation Panel initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize Enhanced Conversation Panel:', error);
      transcriptionStore.setError(`Initialization failed: ${error.message}`);
    }
  });
  
  onDestroy(() => {
    // Cleanup
    if (unsubscribe) {
      unsubscribe();
    }
    
    if (enhancedTranscriptionService) {
      enhancedTranscriptionService.cleanup();
    }
  });
  
  /**
   * Handle state changes for animations and effects
   */
  function handleStateChange(state) {
    // Volume animation
    if (state.volumeLevel > 15 && state.isRecording) {
      volumeAnimation = true;
      setTimeout(() => volumeAnimation = false, 150);
    }
    
    // Text animation when new content arrives
    if (state.liveText !== liveText || state.finalText !== finalText) {
      textAnimation = true;
      setTimeout(() => textAnimation = false, 400);
    }
    
    // Pulse animation for recording state changes
    if (state.isRecording !== isRecording) {
      pulseAnimation = true;
      setTimeout(() => pulseAnimation = false, 600);
    }
  }
  
  /**
   * Handle auto-send functionality
   */
  function handleAutoSend(text) {
    if (!text) return;
    
    accumulatedTranscription += (accumulatedTranscription ? ' ' : '') + text;
    
    const words = accumulatedTranscription.trim().split(' ').filter(word => word.length > 0);
    const timeSinceLastDispatch = (Date.now() - lastDispatchTime) / 1000;
    
    // Check if we should send based on word count or time
    if (words.length >= wordsThreshold || timeSinceLastDispatch >= timeThreshold) {
      dispatch('sendToAssistant', {
        question: accumulatedTranscription.trim(),
        autoSent: true,
        wordCount: words.length,
        timeSinceLastDispatch
      });
      
      // Add system message
      transcriptionStore.addSystemMessage(
        `📤 Auto-sent: ${words.length} words for analysis`
      );
      
      // Reset accumulation
      accumulatedTranscription = '';
      lastDispatchTime = Date.now();
    }
    
    // Enhanced question detection
    if (detectQuestion(text)) {
      dispatch('questionDetected', {
        question: text,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * Start enhanced transcription
   */
  async function startTranscription() {
    try {
      if (!isInitialized) {
        throw new Error('Service not initialized');
      }
      
      await enhancedTranscriptionService.startTranscription();
      
      // Dispatch event
      dispatch('transcriptionStarted', {
        method: transcriptionMethod,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Failed to start transcription:', error);
      transcriptionStore.setError(`Failed to start: ${error.message}`);
      
      dispatch('transcriptionError', {
        error: error.message,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  /**
   * Stop enhanced transcription
   */
  async function stopTranscription() {
    try {
      await enhancedTranscriptionService.stopTranscription();
      
      // Send any remaining accumulated text
      if (autoSendEnabled && accumulatedTranscription.trim()) {
        const finalText = accumulatedTranscription.trim();
        const wordCount = finalText.split(' ').filter(word => word.length > 0).length;
        
        dispatch('sendToAssistant', {
          question: finalText,
          autoSent: true,
          final: true,
          wordCount
        });
        
        transcriptionStore.addSystemMessage(
          `📤 Final batch: ${wordCount} words sent for analysis`
        );
        
        accumulatedTranscription = '';
      }
      
      dispatch('transcriptionStopped', {
        finalText: finalText,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      console.error('Failed to stop transcription:', error);
      transcriptionStore.setError(`Failed to stop: ${error.message}`);
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
    accumulatedTranscription = '';
    dispatch('transcriptionCleared');
  }
  
  /**
   * Change transcription method
   */
  async function changeMethod(newMethod) {
    if (isRecording) {
      await stopTranscription();
    }
    
    transcriptionMethod = newMethod;
    
    try {
      await enhancedTranscriptionService.initialize(transcriptionMethod, {
        showVolume: showVolumeBar,
        showInterim: true,
        autoScroll: true
      });
      
      dispatch('methodChanged', { method: newMethod });
      
    } catch (error) {
      console.error('Failed to change method:', error);
      transcriptionStore.setError(`Failed to switch to ${newMethod}: ${error.message}`);
    }
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
   * Format timestamp
   */
  function formatTimestamp() {
    return new Date().toLocaleTimeString();
  }
  
  /**
   * Auto-scroll to bottom
   */
  async function scrollToBottom() {
    if (conversationHistoryEl && autoScroll) {
      await tick();
      conversationHistoryEl.scrollTop = conversationHistoryEl.scrollHeight;
    }
  }
  
  // Auto-scroll when content changes
  $: if (liveText || finalText) {
    scrollToBottom();
  }
</script>

<div class="enhanced-conversation-panel" class:dark={$darkMode}>
  <!-- Header with controls and status -->
  <div class="panel-header">
    <div class="status-section">
      <div class="status-indicator {getStatusColor(currentStatus)}" 
           class:pulse={pulseAnimation}>
        <div class="status-dot"></div>
        <span class="status-text">{currentStatus}</span>
      </div>
      
      <span class="timestamp">{formatTimestamp()}</span>
    </div>
    
    <!-- Method Selector -->
    <div class="method-selector">
      <button 
        class="method-btn"
        class:active={transcriptionMethod === 'hybrid'}
        on:click={() => changeMethod('hybrid')}
        disabled={isRecording}
        title="Hybrid: Web Speech + Whisper fallback"
      >
        🔀 Hybrid
      </button>
      <button 
        class="method-btn"
        class:active={transcriptionMethod === 'webspeech'}
        on:click={() => changeMethod('webspeech')}
        disabled={isRecording}
        title="Web Speech API (fastest)"
      >
        🌐 Web Speech
      </button>
      <button 
        class="method-btn"
        class:active={transcriptionMethod === 'whisper'}
        on:click={() => changeMethod('whisper')}
        disabled={isRecording}
        title="Whisper API (most accurate)"
      >
        🎯 Whisper
      </button>
    </div>
    
    <!-- Main Controls -->
    <div class="main-controls">
      <button 
        class="control-btn primary"
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
          Stop
        {:else}
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clip-rule="evenodd" />
          </svg>
          Start
        {/if}
      </button>
      
      <button 
        class="control-btn secondary"
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
      <span class="volume-label">Volume:</span>
      <div class="volume-bar-background">
        <div 
          class="volume-bar-fill"
          class:volume-animation={volumeAnimation}
          style="width: {Math.min(100, currentVolume)}%"
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
        aria-label="Dismiss error"
      >
        ✕
      </button>
    </div>
  {/if}
  
  <!-- Auto-send Settings -->
  {#if autoSendEnabled}
    <div class="auto-send-info">
      <span class="auto-send-label">
        📤 Auto-send: {wordsThreshold} words or {timeThreshold}s
      </span>
      {#if accumulatedTranscription.trim()}
        <span class="accumulated-count">
          ({accumulatedTranscription.trim().split(' ').length} words accumulated)
        </span>
      {/if}
    </div>
  {/if}
  
  <!-- Transcription Display -->
  <div class="transcription-display" bind:this={conversationHistoryEl}>
    <!-- Final Text -->
    {#if finalText}
      <div class="final-text" class:text-animation={textAnimation}>
        {finalText}
        <span class="text-timestamp">{formatTimestamp()}</span>
      </div>
    {/if}
    
    <!-- Live Text -->
    {#if liveText && isRecording}
      <div 
        class="live-text"
        class:text-animation={textAnimation}
      >
        <span class="live-indicator">🎤</span>
        <span class="live-content">{liveText}</span>
        <span class="cursor-blink">|</span>
      </div>
    {/if}
    
    <!-- Status Indicators -->
    {#if isRecording && !liveText && !finalText}
      <div class="listening-indicator">
        <div class="listening-dots">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
        <span class="listening-text">Listening for speech...</span>
      </div>
    {:else if !isRecording && !finalText}
      <div class="ready-indicator">
        <span class="ready-text">Click "Start" to begin transcription</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .enhanced-conversation-panel {
    width: 100%;
    background-color: white;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border: 1px solid #e5e7eb;
    overflow: hidden;
    transition: all 0.3s ease;
  }
  
  .enhanced-conversation-panel.dark {
    background-color: #1f2937;
    border-color: #374151;
  }
  
  /* Header */
  .panel-header {
    padding: 1rem;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .dark .panel-header {
    background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
    border-bottom-color: #374151;
  }
  
  .status-section {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 500;
    transition: all 0.3s ease;
  }
  
  .status-indicator.pulse {
    animation: pulse 0.6s ease-in-out;
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
  
  /* Method Selector */
  .method-selector {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
  }
  
  .method-btn {
    padding: 0.5rem 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 6px;
    background: white;
    color: #374151;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  
  .method-btn:hover:not(:disabled) {
    border-color: #d1d5db;
    background: #f9fafb;
  }
  
  .method-btn.active {
    border-color: #3b82f6;
    background: #3b82f6;
    color: white;
  }
  
  .method-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .dark .method-btn {
    background: #374151;
    border-color: #4b5563;
    color: #d1d5db;
  }
  
  .dark .method-btn:hover:not(:disabled) {
    background: #4b5563;
  }
  
  /* Main Controls */
  .main-controls {
    display: flex;
    justify-content: center;
    gap: 1rem;
  }
  
  .control-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    border: 2px solid;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
  }
  
  .control-btn.primary {
    background: #3b82f6;
    border-color: #3b82f6;
    color: white;
  }
  
  .control-btn.primary:hover:not(:disabled) {
    background: #2563eb;
    border-color: #2563eb;
    transform: translateY(-1px);
  }
  
  .control-btn.primary.recording {
    background: #ef4444;
    border-color: #ef4444;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
  }
  
  .control-btn.primary.recording:hover:not(:disabled) {
    background: #dc2626;
    border-color: #dc2626;
  }
  
  .control-btn.secondary {
    background: #f3f4f6;
    border-color: #d1d5db;
    color: #374151;
  }
  
  .control-btn.secondary:hover:not(:disabled) {
    background: #e5e7eb;
  }
  
  .control-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none !important;
  }
  
  .control-btn.pulse {
    animation: pulse 0.6s ease-in-out;
  }
  
  /* Volume Bar */
  .volume-bar-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
  }
  
  .dark .volume-bar-container {
    background: #111827;
    border-bottom-color: #374151;
  }
  
  .volume-label {
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: 500;
  }
  
  .volume-bar-background {
    flex: 1;
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    overflow: hidden;
  }
  
  .dark .volume-bar-background {
    background: #374151;
  }
  
  .volume-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #10b981 0%, #34d399 50%, #fbbf24 80%, #ef4444 100%);
    border-radius: 3px;
    transition: width 0.1s ease;
  }
  
  .volume-bar-fill.volume-animation {
    animation: volumePulse 0.15s ease-out;
  }
  
  .volume-text {
    font-size: 0.75rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
    color: #6b7280;
    min-width: 2.5rem;
    text-align: right;
  }
  
  /* Error Display */
  .error-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
  }
  
  .dark .error-container {
    background: rgba(127, 29, 29, 0.2);
    border-color: #991b1b;
    color: #fca5a5;
  }
  
  .error-icon {
    font-size: 1.125rem;
  }
  
  .error-text {
    flex: 1;
    font-size: 0.875rem;
  }
  
  .error-dismiss {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    font-size: 1.125rem;
    padding: 0.25rem;
  }
  
  /* Auto-send Info */
  .auto-send-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1rem;
    background: #f0f9ff;
    border-bottom: 1px solid #e0f2fe;
    font-size: 0.875rem;
    color: #0369a1;
  }
  
  .dark .auto-send-info {
    background: rgba(2, 132, 199, 0.1);
    border-bottom-color: rgba(2, 132, 199, 0.2);
    color: #7dd3fc;
  }
  
  .accumulated-count {
    color: #0891b2;
  }
  
  /* Transcription Display */
  .transcription-display {
    padding: 1.5rem;
    min-height: 12rem;
    max-height: 20rem;
    overflow-y: auto;
  }
  
  .final-text {
    color: #1f2937;
    line-height: 1.6;
    margin-bottom: 1rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 4px solid #10b981;
  }
  
  .dark .final-text {
    color: #e5e7eb;
    background: #374151;
  }
  
  .final-text.text-animation {
    animation: slideIn 0.4s ease-out;
  }
  
  .text-timestamp {
    display: block;
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.5rem;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  
  .live-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
  }
  
  .dark .live-text {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
  }
  
  .live-text.text-animation {
    animation: liveTextPulse 0.4s ease-out;
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
  
  /* Status Indicators */
  .listening-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 2rem;
    color: #6b7280;
  }
  
  .listening-dots {
    display: flex;
    gap: 0.25rem;
  }
  
  .dot {
    width: 0.5rem;
    height: 0.5rem;
    background: #9ca3af;
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite both;
  }
  
  .dot:nth-child(1) { animation-delay: -0.32s; }
  .dot:nth-child(2) { animation-delay: -0.16s; }
  .dot:nth-child(3) { animation-delay: 0s; }
  
  .listening-text {
    font-size: 0.875rem;
    font-style: italic;
  }
  
  .ready-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    color: #6b7280;
  }
  
  .ready-text {
    font-size: 0.875rem;
    font-style: italic;
  }
  
  /* Icon sizes */
  .w-5 { width: 1.25rem; height: 1.25rem; }
  .w-6 { width: 1.5rem; height: 1.5rem; }
  
  /* Animations */
  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }
  
  @keyframes volumePulse {
    0% { transform: scaleY(1); }
    50% { transform: scaleY(1.3); }
    100% { transform: scaleY(1); }
  }
  
  @keyframes slideIn {
    0% { opacity: 0; transform: translateY(15px); }
    100% { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes liveTextPulse {
    0% { background-color: #eff6ff; }
    50% { background-color: #dbeafe; }
    100% { background-color: #eff6ff; }
  }
  
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
  
  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
  }
  
  /* Responsive */
  @media (max-width: 768px) {
    .panel-header {
      padding: 0.75rem;
    }
    
    .method-selector {
      flex-wrap: wrap;
    }
    
    .method-btn {
      font-size: 0.75rem;
      padding: 0.375rem 0.75rem;
    }
    
    .main-controls {
      flex-direction: column;
      align-items: center;
    }
    
    .transcription-display {
      padding: 1rem;
    }
  }
</style>
