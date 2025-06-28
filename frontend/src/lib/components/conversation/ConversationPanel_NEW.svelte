<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
  import { transcriptionStore } from '$lib/stores/transcription.js';
  import { detectQuestion, extractQuestions } from '$lib/utils/questionDetector.js';
  import { darkMode } from '$lib/stores/ui.js';
  import { whisperTranscriptionService } from '$lib/services/whisperTranscription.js';
  
  const dispatch = createEventDispatcher();
  
  // Transcription mode selection
  let transcriptionMode = 'browser'; // 'browser' or 'whisper'
  
  // Speech Recognition state
  let recognition = null;
  let isRecognitionSupported = false;

  // Audio visualization state
  let audioContext = null;
  let analyser = null;
  let audioStream = null;
  let volumeInterval = null;

  // UI references
  let conversationHistoryEl;
  let autoScroll = true;

  // Animation
  let pulseAnimation = false;
  
  // Auto-send transcription variables
  let accumulatedTranscription = '';
  let lastDispatchTime = Date.now();
  const SECONDS_THRESHOLD = 10;
  // Updated to 15 words for more frequent auto-sending
  const WORDS_THRESHOLD = 15;
  let autoSendEnabled = true; // Add toggle for auto-sending
  
  // Function to estimate speech duration based on word count
  function estimateSpeechDuration(text) {
    // Simple estimation based on word count (average speaking rate)
    const words = text.trim().split(' ').filter(word => word.length > 0).length;
    // Assuming 2.5 words per second (150 words per minute)
    return words / 2.5; // Returns duration in seconds
  }
  
  // Function to check if accumulated text should be sent
  function checkAndSendAccumulated() {
    if (!accumulatedTranscription.trim() || !autoSendEnabled) return;
    
    // Calculate estimated speech duration
    const estimatedDuration = estimateSpeechDuration(accumulatedTranscription);
    const wordCount = accumulatedTranscription.split(' ').filter(word => word.length > 0).length;
    
    // Send if we've accumulated 15 words or roughly 6 seconds of speech
    if (wordCount >= WORDS_THRESHOLD || estimatedDuration >= 6) {
      const textToSend = accumulatedTranscription.trim();
      console.log(`Auto-sending ${estimatedDuration.toFixed(1)}s worth of transcription (${wordCount} words)`);
      
      // Dispatch event with the accumulated transcription
      dispatch('sendToAssistant', { 
        question: textToSend,
        autoSent: true
      });
      
      // Add indicator in the conversation that content was sent for analysis
      transcriptionStore.addSystemMessage(`📤 Sent ${wordCount} words to AI assistant for analysis and gap detection`);
      
      // Reset accumulation after sending
      accumulatedTranscription = '';
      lastDispatchTime = Date.now();
    }
  }

  // Toggle auto-sending feature
  function toggleAutoSend() {
    autoSendEnabled = !autoSendEnabled;
    if (!autoSendEnabled && accumulatedTranscription.trim()) {
      // Clear accumulated transcription when disabling
      accumulatedTranscription = '';
    }
  }

  onMount(() => {
    // Check if browser supports required APIs
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      isRecognitionSupported = true;
      setupSpeechRecognition(SpeechRecognition);
    } else {
      transcriptionStore.setError("Your browser doesn't support speech recognition. Try using Chrome, Edge, or Safari.");
    }
    
    // Initialize Whisper service event listeners
    setupWhisperEventListeners();
    
    // Handle scroll position changes to detect manual scrolling
    if (conversationHistoryEl) {
      conversationHistoryEl.addEventListener('scroll', handleScroll);
    }
    
    // Initialize pulse animation
    startPulseAnimation();
  });
  
  onDestroy(() => {
    stopRecording();
    stopVolumeMonitoring();
    
    // Disconnect Whisper service
    if (whisperTranscriptionService) {
      whisperTranscriptionService.disconnect();
    }
    
    // Remove Whisper event listeners
    if (typeof window !== 'undefined') {
      window.removeEventListener('whisperSentence', handleWhisperSentence);
    }
    
    // Clean up scroll listener
    if (conversationHistoryEl) {
      conversationHistoryEl.removeEventListener('scroll', handleScroll);
    }
  });
  
  function handleScroll() {
    if (!conversationHistoryEl) return;
    
    const { scrollTop, scrollHeight, clientHeight } = conversationHistoryEl;
    const isAtBottom = Math.abs((scrollTop + clientHeight) - scrollHeight) < 10;
    
    // Only update autoScroll if user has scrolled manually
    if (!isAtBottom && autoScroll) {
      autoScroll = false;
    } else if (isAtBottom && !autoScroll) {
      autoScroll = true;
    }
  }
  
  function scrollToBottom() {
    if (!autoScroll || !conversationHistoryEl) return;
    
    tick().then(() => {
      conversationHistoryEl.scrollTop = conversationHistoryEl.scrollHeight;
    });
  }
  
  // Subscribe to message changes to trigger autoscroll
  const unsubscribe = transcriptionStore.subscribe(state => {
    if (state.messages.length > 0) {
      scrollToBottom();
    }
  });
  
  // Animation for recording indicator
  function startPulseAnimation() {
    pulseAnimation = true;
    setTimeout(() => {
      pulseAnimation = false;
    }, 1000);
    
    // If recording, continue the animation
    if ($transcriptionStore.isRecording) {
      setTimeout(startPulseAnimation, 1500);
    }
  }
  
  function setupSpeechRecognition(SpeechRecognition) {
    recognition = new SpeechRecognition();
    
    // Configure recognition
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US'; // Can be made configurable
    
    // Handle results
    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      
      // Update live text with interim results
      if (interimTranscript) {
        transcriptionStore.updateLiveText(interimTranscript);
        transcriptionStore.setStatus("transcribing");
      }
      
      // Process final text
      if (finalTranscript) {
        transcriptionStore.updateFinalText(finalTranscript);
        transcriptionStore.setStatus("completed");
        
        // Add as a conversation message
        transcriptionStore.addMessage(finalTranscript);
        
        // Add to accumulated transcription for auto-sending if enabled
        if (autoSendEnabled) {
          accumulatedTranscription += ' ' + finalTranscript;
          accumulatedTranscription = accumulatedTranscription.trim();
          
          // Check if we should send accumulated content
          checkAndSendAccumulated();
        }
        
        // Enhanced question detection using questionDetector utility
        if (detectQuestion(finalTranscript)) {
          dispatch('questionDetected', {
            question: finalTranscript
          });
        }
      }
    };
    
    // Handle errors
    recognition.onerror = (event) => {
      console.error('Speech Recognition Error:', event.error);
      
      let errorMessage = 'Error with speech recognition: ';
      
      switch (event.error) {
        case 'not-allowed':
          errorMessage += 'Microphone access was denied.';
          break;
        case 'no-speech':
          errorMessage += 'No speech was detected.';
          break;
        case 'network':
          errorMessage += 'Network error occurred.';
          break;
        default:
          errorMessage += event.error;
      }
      
      transcriptionStore.setError(errorMessage);
      transcriptionStore.setStatus("error");
      stopBrowserRecording();
    };
    
    recognition.onend = () => {
      // If we're still supposed to be recording, restart recognition
      // (recognition will auto-stop after periods of silence)
      if (transcriptionStore.subscribe(val => val.isRecording)()) {
        try {
          recognition.start();
        } catch (e) {
          // Ignore errors trying to restart while already started
          console.warn('Error restarting recognition:', e);
        }
      } else {
        transcriptionStore.setStatus("ready");
      }
    };
  }
  
  // Whisper-specific functions
  function setupWhisperEventListeners() {
    // Listen for Whisper sentence events
    if (typeof window !== 'undefined') {
      window.addEventListener('whisperSentence', handleWhisperSentence);
    }
  }
  
  function handleWhisperSentence(event) {
    const { text, language, timestamp, isFinal, hotmic } = event.detail;
    
    // Add to accumulated transcription for auto-sending if enabled
    if (autoSendEnabled && text) {
      accumulatedTranscription += ' ' + text;
      accumulatedTranscription = accumulatedTranscription.trim();
      
      // Check if we should send accumulated content
      checkAndSendAccumulated();
    }
    
    // Enhanced question detection
    if (detectQuestion(text)) {
      dispatch('questionDetected', {
        question: text
      });
    }
  }
  
  async function startWhisperRecording() {
    if (!whisperTranscriptionService) {
      transcriptionStore.setError('Whisper service not available');
      return;
    }
    
    try {
      transcriptionStore.setStatus('connecting');
      
      // Connect to Whisper service
      const connected = await whisperTranscriptionService.connect({
        language: null, // auto-detect
        model: 'base' // Can be made configurable
      });
      
      if (!connected) {
        throw new Error('Failed to connect to Whisper service');
      }
      
      // Start recording
      await whisperTranscriptionService.startRecording();
      
      transcriptionStore.setStatus('recording');
      transcriptionStore.setRecording(true);
      
      console.log('Whisper recording started');
      
    } catch (error) {
      console.error('Error starting Whisper recording:', error);
      transcriptionStore.setError(`Failed to start Whisper recording: ${error.message}`);
      transcriptionStore.setStatus('error');
    }
  }
  
  function stopWhisperRecording() {
    if (!whisperTranscriptionService) {
      return;
    }
    
    try {
      whisperTranscriptionService.stopRecording();
      
      // Send any remaining accumulated transcription before stopping
      if (autoSendEnabled && accumulatedTranscription.trim()) {
        const finalText = accumulatedTranscription.trim();
        const wordCount = finalText.split(' ').filter(word => word.length > 0).length;
        
        dispatch('sendToAssistant', { 
          question: finalText,
          autoSent: true,
          final: true
        });
        
        transcriptionStore.addSystemMessage(`📤 Final batch: ${wordCount} words sent for analysis and gap detection`);
        accumulatedTranscription = '';
      }
      
      transcriptionStore.setRecording(false);
      transcriptionStore.setStatus('ready');
      
      console.log('Whisper recording stopped');
      
    } catch (error) {
      console.error('Error stopping Whisper recording:', error);
      transcriptionStore.setError(`Error stopping Whisper recording: ${error.message}`);
    }
  }
  
  // Modified recording functions to handle both modes
  function startRecording() {
    if (transcriptionMode === 'whisper') {
      startWhisperRecording();
    } else {
      startBrowserRecording();
    }
  }
  
  function stopRecording() {
    if (transcriptionMode === 'whisper') {
      stopWhisperRecording();
    } else {
      stopBrowserRecording();
    }
  }
  
  function startBrowserRecording() {
    try {
      if (!isRecognitionSupported) {
        transcriptionStore.setError("Speech recognition is not supported in this browser.");
        return;
      }
      
      transcriptionStore.setStatus("requesting_permission");
      
      // Request microphone permission and start recognition
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          // Store the stream for cleanup
          audioStream = stream;
          
          // Start volume monitoring
          startVolumeMonitoring(stream);
          
          // Start speech recognition
          try {
            recognition.start();
            transcriptionStore.setRecording(true);
            transcriptionStore.setConnected(true);
            transcriptionStore.setStatus("recording");
            
            // Start pulse animation
            startPulseAnimation();
            
          } catch (error) {
            // Recognition might already be running
            console.warn("Speech recognition start error:", error);
            transcriptionStore.setRecording(true);
            transcriptionStore.setConnected(true);
            transcriptionStore.setStatus("recording");
          }
        })
        .catch(error => {
          console.error("Microphone permission denied:", error);
          transcriptionStore.setError(`Microphone access denied: ${error.message}`);
          transcriptionStore.setStatus("error");
        });
        
    } catch (error) {
      console.error("Error starting recording:", error);
      transcriptionStore.setError(`Error starting recording: ${error.message}`);
      transcriptionStore.setStatus("error");
    }
  }
  
  function stopBrowserRecording() {
    try {
      if (recognition) {
        recognition.stop();
      }
      
      transcriptionStore.setRecording(false);
      transcriptionStore.setConnected(false);
      transcriptionStore.setStatus("ready");
      
      // Send any remaining accumulated transcription before stopping
      if (autoSendEnabled && accumulatedTranscription.trim()) {
        const finalText = accumulatedTranscription.trim();
        const wordCount = finalText.split(' ').filter(word => word.length > 0).length;
        
        dispatch('sendToAssistant', { 
          question: finalText,
          autoSent: true,
          final: true
        });
        
        transcriptionStore.addSystemMessage(`📤 Final batch: ${wordCount} words sent for analysis and gap detection`);
        accumulatedTranscription = '';
      }
      
      // Clean up resources
      cleanupResources();
      
    } catch (error) {
      console.error("Error stopping recording:", error);
      transcriptionStore.setError(`Error stopping recording: ${error.message}`);
      
      // Ensure we still clean up even if there's an error
      cleanupResources();
    }
  }
  
  function startVolumeMonitoring(stream) {
    if (!window.AudioContext && !window.webkitAudioContext) {
      console.warn('AudioContext not supported - volume visualization unavailable');
      return;
    }
    
    try {
      // Create audio context
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      analyser = audioContext.createAnalyser();
      
      // Connect the microphone stream to the analyser
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      
      // Configure the analyser
      analyser.fftSize = 256;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      // Set up interval for volume monitoring
      volumeInterval = setInterval(() => {
        if (analyser) {
          analyser.getByteFrequencyData(dataArray);
          
          // Calculate volume level (simple average)
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          
          // Normalize volume (0-100)
          const volumeLevel = Math.min(100, Math.max(0, sum / bufferLength * 2));
          transcriptionStore.setVolumeLevel(volumeLevel);
        }
      }, 100);
    } catch (e) {
      console.warn('Error setting up audio visualization:', e);
    }
  }
  
  function stopVolumeMonitoring() {
    if (volumeInterval) {
      clearInterval(volumeInterval);
      volumeInterval = null;
    }
    
    if (analyser) {
      analyser = null;
    }
    
    if (audioContext) {
      audioContext.close().catch(e => console.warn('Error closing audio context:', e));
      audioContext = null;
    }
  }
  
  function cleanupResources() {
    // Stop audio stream tracks
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      audioStream = null;
    }
    
    // Stop volume monitoring
    stopVolumeMonitoring();
    
    // Reset volume level
    transcriptionStore.setVolumeLevel(0);
  }

  // Handle drag and drop functionality
  function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }

  function handleDropMessage(event, messageText) {
    event.preventDefault();
    
    // Dispatch event to parent component (console) to handle the drop
    dispatch('conversationDrop', {
      text: messageText
    });
  }

  // Handle conversation message clicks
  function handleMessageClick(messageText) {
    dispatch('conversationMessageClick', {
      text: messageText
    });
  }
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
  <header class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
    <div class="flex justify-between items-center">
      <div class="flex items-center space-x-3">
        <div class="p-2 bg-blue-600 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-white">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="23"></line>
            <line x1="8" y1="23" x2="16" y2="23"></line>
          </svg>
        </div>
        <h2 class="text-xl font-bold text-gray-800 dark:text-gray-100">Hot Mic</h2>
      </div>
      <div class="flex items-center space-x-3">
        <!-- Transcription Mode Selector -->
        <div class="flex items-center space-x-2 bg-gray-100 dark:bg-gray-600 p-1 rounded-lg border border-gray-200 dark:border-gray-600">
          <button 
            class={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              transcriptionMode === 'browser' 
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm border border-blue-200 dark:border-blue-500' 
                : 'text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700'
            }`}
            on:click={() => transcriptionMode = 'browser'}
            disabled={$transcriptionStore.isRecording}
            title="Use browser's built-in speech recognition"
          >
            Browser
          </button>
          <button 
            class={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              transcriptionMode === 'whisper' 
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm border border-blue-200 dark:border-blue-500' 
                : 'text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-700'
            }`}
            on:click={() => transcriptionMode = 'whisper'}
            disabled={$transcriptionStore.isRecording}
            title="Use OpenAI Whisper for high-quality transcription"
          >
            Whisper
          </button>
        </div>
        
        <button 
          class={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${autoSendEnabled ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-100 dark:bg-gray-600 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-500'}`}
          on:click={toggleAutoSend} 
          title="Toggle automatic sending of transcriptions every 15 words"
        >
          {#if autoSendEnabled}
            🔄 Auto-Send On
          {:else}
            ⏸️ Auto-Send Off
          {/if}
        </button>
        <button class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 border border-gray-300 dark:border-gray-500 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors" on:click={() => transcriptionStore.resetMessages()}>
          Clear History
        </button>
      </div>
    </div>
  </header>

  <div class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
    <div class="flex items-center justify-between">
      {#if !$transcriptionStore.isRecording}
        <button 
          class="px-6 py-3 bg-blue-600 text-white rounded-lg flex items-center space-x-3 hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          on:click={startRecording}
          disabled={$transcriptionStore.status === 'connecting' || $transcriptionStore.status === 'requesting_permission'}
        >
          <div class="p-1 bg-blue-500 rounded">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" class="text-white">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          </div>
          <span>Start Recording</span>
        </button>
      {:else}
        <button 
          class="px-6 py-3 bg-red-600 text-white rounded-lg flex items-center space-x-3 hover:bg-red-700 transition-colors font-medium"
          on:click={stopRecording}
        >
          <div class="p-1 bg-red-500 rounded">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" class="text-white">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            </svg>
          </div>
          <span>Stop Recording</span>
        </button>
      {/if}
      
      <div class="flex items-center space-x-4 flex-1 mx-6">
        <div class="flex items-center space-x-3">
          <span class={`inline-block w-4 h-4 rounded-full ${
            $transcriptionStore.status === 'recording' 
              ? 'bg-red-500 ' + (pulseAnimation ? 'animate-pulse' : '') 
              : $transcriptionStore.status === 'error' 
                ? 'bg-red-600' 
                : $transcriptionStore.status === 'connecting' || $transcriptionStore.status === 'requesting_permission' || $transcriptionStore.status === 'transcribing' 
                  ? 'bg-yellow-500' 
                  : 'bg-green-500'
          }`}></span>
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
            {#if $transcriptionStore.status === 'ready'}
              Ready ({transcriptionMode === 'whisper' ? 'Whisper' : 'Browser'})
            {:else if $transcriptionStore.status === 'requesting_permission'}
              Requesting microphone...
            {:else if $transcriptionStore.status === 'connecting'}
              Connecting ({transcriptionMode === 'whisper' ? 'Whisper' : 'Browser'})...
            {:else if $transcriptionStore.status === 'recording'}
              Recording ({transcriptionMode === 'whisper' ? 'Whisper' : 'Browser'})
            {:else if $transcriptionStore.status === 'transcribing'}
              Transcribing ({transcriptionMode === 'whisper' ? 'Whisper' : 'Browser'})...
            {:else if $transcriptionStore.status === 'completed'}
              Completed
            {:else if $transcriptionStore.status === 'error'}
              Error
            {/if}
          </span>
        </div>
        
        {#if $transcriptionStore.isRecording && $transcriptionStore.volumeLevel > 0}
          <div class="flex-1 max-w-xs h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden border border-gray-300 dark:border-gray-500">
            <div class="h-full bg-blue-500 dark:bg-blue-400 transition-all duration-150" style="width: {$transcriptionStore.volumeLevel}%"></div>
          </div>
        {/if}
      </div>

      <div class="flex items-center">
        <label class="inline-flex items-center cursor-pointer">
          <input type="checkbox" bind:checked={autoScroll} class="sr-only peer">
          <div class="relative w-12 h-6 bg-gray-200 dark:bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-6 peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 border border-gray-300 dark:border-gray-500"></div>
          <span class="ml-3 text-sm font-medium text-gray-700 dark:text-gray-300">Auto-scroll</span>
        </label>
      </div>
    </div>
  </div>
  
  {#if $transcriptionStore.errorMessage}
    <div class="mx-4 mt-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2 dark:bg-red-900 dark:text-red-300">
      <span class="text-sm">⚠️</span>
      <span class="text-sm flex-1">{$transcriptionStore.errorMessage}</span>
      <button class="p-1 text-lg text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300" on:click={() => transcriptionStore.setError(null)}>×</button>
    </div>
  {/if}
  
  <div class={`mx-6 mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 min-h-[80px] flex items-center ${$transcriptionStore.liveText ? 'border-blue-400 dark:border-blue-500' : ''}`}>
    {#if $transcriptionStore.liveText}
      <div class="text-gray-800 dark:text-gray-200 italic font-medium">{$transcriptionStore.liveText}</div>
    {:else if $transcriptionStore.isRecording}
      <div class="text-gray-500 dark:text-gray-400 italic">Listening...</div>
    {:else}
      <div class="text-gray-500 dark:text-gray-400 italic">Live transcription will appear here...</div>
    {/if}
  </div>
  
  <div class="flex-1 p-6 overflow-hidden">
    <div class="h-full overflow-y-auto space-y-3" bind:this={conversationHistoryEl}>
      {#if $transcriptionStore.messages.length > 0}
        {#each $transcriptionStore.messages as message (message.id)}
          <div 
            class={`p-4 rounded-lg border transition-colors cursor-pointer hover:shadow-md ${
              message.isSystem 
                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700 text-blue-800 dark:text-blue-200' 
                : message.isQuestion 
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700 text-green-800 dark:text-green-200' 
                  : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-200'
            }`}
            role="button"
            tabindex="0"
            aria-label="Click to send message to assistant"
            draggable="true"
            on:click={() => handleMessageClick(message.text)}
            on:keydown={(e) => e.key === 'Enter' && handleMessageClick(message.text)}
            on:dragstart={(e) => e.dataTransfer.setData('text/plain', message.text)}
            on:dragover={handleDragOver}
            on:drop={(e) => handleDropMessage(e, message.text)}
          >
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <p class="text-sm font-medium mb-1">{message.text}</p>
                <div class="flex items-center space-x-2 text-xs opacity-75">
                  <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                  {#if message.isQuestion}
                    <span class="px-2 py-1 bg-green-200 dark:bg-green-800 rounded-full text-green-800 dark:text-green-200">Question</span>
                  {/if}
                  {#if message.isSystem}
                    <span class="px-2 py-1 bg-blue-200 dark:bg-blue-800 rounded-full text-blue-800 dark:text-blue-200">System</span>
                  {/if}
                </div>
              </div>
              <div class="text-gray-400 dark:text-gray-500 text-xs">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 18l6-6-6-6"/>
                </svg>
              </div>
            </div>
          </div>
        {/each}
      {:else}
        <div class="flex flex-col items-center justify-center h-full text-center py-12">
          <div class="p-4 bg-gray-100 dark:bg-gray-700 rounded-full mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 dark:text-gray-500">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
              <line x1="12" y1="19" x2="12" y2="23"></line>
              <line x1="8" y1="23" x2="16" y2="23"></line>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">Ready to Listen</h3>
          <p class="text-gray-500 dark:text-gray-400 max-w-sm">No conversation recorded yet. Click "Start Recording" to begin capturing audio and transcribing in real-time with automatic gap detection.</p>
        </div>
      {/if}
    </div>
  </div>
</div>
