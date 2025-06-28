<script>
  import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
  import { whisperStore } from '$lib/stores/whisperStore.js';
  import { transcribeAudio, detectQuestionsWithLLM } from '$lib/services/apiService.js';
  import { extractQuestions, detectQuestion } from '$lib/utils/questionDetector.js';
  
  const dispatch = createEventDispatcher();
  
  // Audio recording state
  let mediaRecorder = null;
  let recordingInterval = null;
  let audioChunks = [];
  let recordingStartTime = null;
  let currentRecordingDuration = 0;
  let lastTranscriptionTime = 0;
  
  // Recording format
  let selectedMimeType = null;
  
  // Audio visualization state
  let audioContext = null;
  let analyser = null;
  let audioStream = null;
  let volumeInterval = null;

  // UI references
  let transcriptionHistoryEl;
  let autoScroll = true;
  
  // Constants
  const TRANSCRIPTION_INTERVAL = 5000; // Transcribe every 5 seconds
  const MAX_RECORDING_DURATION = 30000; // 30 seconds max continuous recording - reduced from 60s to minimize issues
  
  // Animation state
  let pulseAnimation = false;
  
  // List of supported MIME types for Whisper API
  const supportedMimeTypes = [
    'audio/webm',
    'audio/wav',
    'audio/mp3',
    'audio/mp4',
    'audio/mpeg',
    'audio/ogg'
  ];
  
  // Find the first supported MIME type for the browser
  function getBestSupportedMimeType() {
    // Prioritize specific codecs that work well with Whisper API
    const mimeTypesToCheck = [
      'audio/webm',
      'audio/mp3',
      'audio/wav',
      'audio/ogg'
    ];
    
    for (const mimeType of mimeTypesToCheck) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        console.log(`Selected MIME type: ${mimeType}`);
        return mimeType;
      }
    }
    
    // Fallback to a basic type
    return 'audio/webm';
  }
  
  onMount(() => {
    if (transcriptionHistoryEl) {
      transcriptionHistoryEl.addEventListener('scroll', handleScroll);
    }
    
    // Check if browser supports required APIs
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      whisperStore.setError("Your browser doesn't support audio recording. Try using Chrome, Edge, or Safari.");
    }
  });
  
  onDestroy(() => {
    stopRecording();
    clearVolumeMonitoring();
    
    if (transcriptionHistoryEl) {
      transcriptionHistoryEl.removeEventListener('scroll', handleScroll);
    }
    
    if (recordingInterval) {
      clearInterval(recordingInterval);
    }
  });
  
  function handleScroll() {
    if (!transcriptionHistoryEl) return;
    
    const { scrollTop, scrollHeight, clientHeight } = transcriptionHistoryEl;
    const isAtBottom = Math.abs((scrollTop + clientHeight) - scrollHeight) < 10;
    
    // Only update autoScroll if user has scrolled manually
    if (!isAtBottom && autoScroll) {
      autoScroll = false;
    } else if (isAtBottom && !autoScroll) {
      autoScroll = true;
    }
  }
  
  function scrollToBottom() {
    if (!autoScroll || !transcriptionHistoryEl) return;
    
    tick().then(() => {
      transcriptionHistoryEl.scrollTop = transcriptionHistoryEl.scrollHeight;
    });
  }
  
  // Subscribe to message changes to trigger autoscroll
  const unsubscribe = whisperStore.subscribe(state => {
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
    if ($whisperStore.isRecording) {
      setTimeout(startPulseAnimation, 1500);
    }
  }

  async function startRecording() {
    try {
      // Reset state
      whisperStore.setError(null);
      whisperStore.setStatus("requesting_permission");
      whisperStore.updateLiveText("");
      whisperStore.updateFinalText("");
      audioChunks = [];
      whisperStore.clearAudioChunks();
      currentRecordingDuration = 0;
      lastTranscriptionTime = Date.now();
      
      // Get microphone access
      audioStream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      // Set up audio analysis for volume visualization
      setupVolumeMonitoring(audioStream);
      
      // Get the best supported MIME type for consistent format
      selectedMimeType = getBestSupportedMimeType();
      console.log(`Using MIME type: ${selectedMimeType}`);
      
      mediaRecorder = new MediaRecorder(audioStream, {
        mimeType: selectedMimeType,
        audioBitsPerSecond: 128000 // 128 kbps for good quality audio
      });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log(`Audio chunk received, size: ${event.data.size} bytes, type: ${event.data.type}`);
          audioChunks.push(event.data);
          whisperStore.addAudioChunk(event.data);
        }
      };
      
      mediaRecorder.onstart = () => {
        recordingStartTime = Date.now();
        whisperStore.setRecording(true);
        whisperStore.setStatus("recording");
        whisperStore.setConnectedToMic(true);
        
        // Set up interval for continuous transcription
        recordingInterval = setInterval(async () => {
          currentRecordingDuration = Date.now() - recordingStartTime;
          
          // If enough time has passed, perform an interim transcription
          if (Date.now() - lastTranscriptionTime >= TRANSCRIPTION_INTERVAL && audioChunks.length > 0) {
            console.log(`Interval transcription after ${(Date.now() - lastTranscriptionTime)/1000}s`);
            await requestTranscription(false);
          }
          
          // If recording is too long, restart it to avoid memory issues
          if (currentRecordingDuration >= MAX_RECORDING_DURATION) {
            console.log(`Maximum duration reached (${MAX_RECORDING_DURATION/1000}s), restarting recording`);
            restartRecording();
          }
        }, 1000);
      };
      
      // Start recording
      mediaRecorder.start(1000); // Capture data in 1-second chunks
      startPulseAnimation();
      
    } catch (error) {
      console.error("Error starting recording:", error);
      
      if (error.name === "NotAllowedError") {
        whisperStore.setError("Microphone access denied. Please allow microphone access and try again.");
      } else if (error.name === "NotFoundError") {
        whisperStore.setError("No microphone found. Please connect a microphone and try again.");
      } else {
        whisperStore.setError(`Error starting recording: ${error.message}`);
      }
      
      whisperStore.setStatus("error");
      cleanupResources();
    }
  }

  async function stopRecording() {
    try {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
      
      if (recordingInterval) {
        clearInterval(recordingInterval);
        recordingInterval = null;
      }
      
      whisperStore.setRecording(false);
      whisperStore.setConnectedToMic(false);
      
      // Process final audio if there are chunks
      if (audioChunks.length > 0) {
        await requestTranscription(true);
      }
      
      whisperStore.setStatus("ready");
      
      // Clean up resources
      cleanupResources();
      
    } catch (error) {
      console.error("Error stopping recording:", error);
      whisperStore.setError(`Error stopping recording: ${error.message}`);
      cleanupResources();
    }
  }
  
  async function requestTranscription(isFinal = false) {
    try {
      if (audioChunks.length === 0) return;
      
      // Create a copy of the chunks to avoid modifying the original array
      const chunksToProcess = [...audioChunks];
      
      // Create a blob with the proper MIME type
      const audioBlob = new Blob(chunksToProcess, { type: selectedMimeType });
      
      // Only proceed if we have audio data (more robust check)
      if (audioBlob.size < 100) {
        console.log('Audio data too small, skipping transcription');
        return;
      }
      
      whisperStore.setStatus("transcribing");
      whisperStore.setProcessing(true);
      
      console.log(`Transcribing audio: ${Math.round(audioBlob.size / 1024)}KB, MIME type: ${selectedMimeType}, isFinal: ${isFinal}`);
      
      try {
        // Transcribe the audio using Whisper API
        const transcribedText = await transcribeAudio(audioBlob);
        
        if (transcribedText && transcribedText.trim() !== '') {
          console.log('Transcription successful:', transcribedText);
          
          if (isFinal) {
            // Add the message to the transcript history
            whisperStore.addMessage(transcribedText); 
            whisperStore.updateFinalText(transcribedText);
            
            // Analyze for questions using enhanced detection
            await detectQuestionsInTranscription(transcribedText);
          } else {
            whisperStore.updateLiveText(transcribedText);
          }
        } else {
          console.log('Transcription returned empty text');
        }
        
        whisperStore.setStatus(isFinal ? "completed" : "recording");
      } catch (transcriptionError) {
        console.error("Transcription API error:", transcriptionError);
        
        // Don't show errors for intermediate transcriptions
        if (isFinal) {
          whisperStore.setError(`Couldn't transcribe audio: ${transcriptionError.message}`);
          whisperStore.setStatus("error");
        } else {
          // For intermediate transcription errors, just log and continue
          console.log("Intermediate transcription failed, continuing recording");
          whisperStore.setStatus("recording");
        }
      }
      
      // Reset for next recording segment if not final
      if (!isFinal) {
        // Clear the audio chunks to avoid format issues in subsequent transcriptions
        audioChunks = [];
        lastTranscriptionTime = Date.now();
      }
      
    } catch (error) {
      console.error("Error during transcription process:", error);
      whisperStore.setError(`Transcription process error: ${error.message}`);
      whisperStore.setStatus("error");
    } finally {
      whisperStore.setProcessing(false);
    }
  }
  
  async function detectQuestionsInTranscription(text) {
    if (!text || text.trim().length < 10) {
      console.log('Text too short for question detection, skipping');
      return;
    }
    
    try {
      // Set a status to show we're analyzing the text
      whisperStore.setStatus("analyzing");
      
      // Enhanced question detection approach:
      // 1. Fast local detection for explicit questions
      // 2. Use GPT-4o for deeper contextual understanding
      
      console.log('Phase 1: Detecting explicit questions using local utility:', text.substring(0, 50) + '...');
      
      // Step 1: Detect explicit questions using the local utility (fast)
      const explicitQuestions = extractQuestions(text, false);  // Don't include implicit questions yet
      const allDetectedQuestions = [];
      
      if (explicitQuestions && explicitQuestions.length > 0) {
        console.log(`Detected ${explicitQuestions.length} explicit questions using local detection`);
        
        // Clean and normalize explicit questions
        const cleanedExplicitQuestions = cleanQuestions(explicitQuestions);
        
        if (cleanedExplicitQuestions.length > 0) {
          console.log(`After cleaning, we have ${cleanedExplicitQuestions.length} explicit questions`);
          
          // Add explicit questions to our collection
          allDetectedQuestions.push(...cleanedExplicitQuestions);
          
          // Add explicit questions to the whisper store for UI display
          cleanedExplicitQuestions.forEach(question => {
            whisperStore.addDetectedQuestion(question);
          });
        }
      }
      
      // Step 2: Always use the LLM for deeper contextual analysis
      try {
        console.log('Phase 2: Performing GPT-4o question and knowledge gap detection');
        const llmQuestions = await detectQuestionsWithLLM(text);
        
        if (llmQuestions && llmQuestions.length > 0) {
          console.log(`Detected ${llmQuestions.length} raw questions/knowledge gaps with GPT-4o`);
          
          // Clean and normalize LLM questions
          const cleanedLlmQuestions = cleanQuestions(llmQuestions);
          
          // Filter out questions that are very similar to ones already detected
          const uniqueLlmQuestions = cleanedLlmQuestions.filter(llmQ => {
            return !allDetectedQuestions.some(existingQ => areQuestionsSimilar(existingQ, llmQ));
          });
          
          if (uniqueLlmQuestions.length > 0) {
            console.log(`Adding ${uniqueLlmQuestions.length} unique questions/knowledge gaps from GPT-4o`);
            
            // Add the unique LLM questions to the whisper store
            uniqueLlmQuestions.forEach(question => {
              whisperStore.addDetectedQuestion(question);
            });
            
            // Add to our collection of all detected questions
            allDetectedQuestions.push(...uniqueLlmQuestions);
          }
        }
      } catch (llmError) {
        console.error("Error detecting questions with GPT-4o:", llmError);
      }
      
      // If we found any questions, notify the parent component
      if (allDetectedQuestions.length > 0) {
        console.log(`Processing ${allDetectedQuestions.length} total detected questions`);
        
        // Notify parent component about all detected questions
        dispatch('questionsDetected', { questions: allDetectedQuestions });
      }
    } catch (error) {
      console.error("Error detecting questions:", error);
    } finally {
      // Reset status to completed
      whisperStore.setStatus("completed");
    }
  }
  
  async function restartRecording() {
    try {
      // Process current audio
      if (audioChunks.length > 0) {
        await requestTranscription(false);
      }
      
      // Stop current recorder
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        
        // Short timeout to ensure the recorder has time to stop
        setTimeout(() => {
          // Clear chunks before starting new recording to avoid format issues
          audioChunks = [];
          
          if (audioStream) {
            // Create a new MediaRecorder with the same stream and MIME type
            mediaRecorder = new MediaRecorder(audioStream, {
              mimeType: selectedMimeType,
              audioBitsPerSecond: 128000
            });
            
            mediaRecorder.ondataavailable = (event) => {
              if (event.data.size > 0) {
                console.log(`Audio chunk received on restart, size: ${event.data.size} bytes, type: ${event.data.type}`);
                audioChunks.push(event.data);
                whisperStore.addAudioChunk(event.data);
              }
            };
            
            recordingStartTime = Date.now();
            lastTranscriptionTime = Date.now(); // Reset transcription timer
            mediaRecorder.start(1000);
          }
        }, 200);
      }
    } catch (error) {
      console.error("Error restarting recording:", error);
      whisperStore.setError(`Error restarting recording: ${error.message}. Please try stopping and starting the recording again.`);
      
      // Emergency cleanup
      cleanupResources();
      whisperStore.setStatus("error");
    }
  }
  
  function setupVolumeMonitoring(stream) {
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
          
          // Calculate average volume
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          
          const average = sum / bufferLength;
          const normalizedVolume = Math.min(1, average / 128);
          
          whisperStore.setVolumeLevel(normalizedVolume);
        }
      }, 100);
    } catch (e) {
      console.warn('Error setting up audio visualization:', e);
    }
  }
  
  function clearVolumeMonitoring() {
    if (volumeInterval) {
      clearInterval(volumeInterval);
      volumeInterval = null;
    }
    
    if (analyser) {
      analyser = null;
    }
    
    if (audioContext) {
      try {
        audioContext.close();
      } catch (e) {
        console.warn('Error closing audio context:', e);
      }
      audioContext = null;
    }
  }
  
  function cleanupResources() {
    // Stop media recorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      try {
        mediaRecorder.stop();
      } catch (e) {
        console.warn('Error stopping mediaRecorder:', e);
      }
    }
    
    // Stop all audio tracks
    if (audioStream) {
      audioStream.getTracks().forEach(track => track.stop());
      audioStream = null;
    }
    
    // Clear intervals
    if (recordingInterval) {
      clearInterval(recordingInterval);
      recordingInterval = null;
    }
    
    clearVolumeMonitoring();
  }
  
  // Status indicator color mapping
  $: statusColor = getStatusColor($whisperStore.status);
  $: volumeHeight = Math.max(4, Math.round($whisperStore.volumeLevel * 36)); // Min 4px, max 36px

  function getStatusColor(status) {
    switch(status) {
      case "recording": return "bg-red-500";
      case "transcribing": return "bg-blue-500";
      case "completed": return "bg-green-500";
      case "error": return "bg-orange-500";
      default: return "bg-gray-400";
    }
  }
</script>

<div class="flex flex-col h-full overflow-hidden rounded-lg shadow-md bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100">
  <!-- Header -->
  <header class="flex justify-between items-center px-4 py-3 border-b border-gray-200 dark:border-gray-700">
    <h2 class="text-xl font-semibold">Whisper Transcription</h2>
    <div class="flex items-center space-x-2">
      <button 
        on:click={() => whisperStore.resetMessages()}
        class="p-1.5 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
        aria-label="Clear conversation"
        title="Clear conversation"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  </header>

  <!-- Control Bar -->
  <div class="flex flex-wrap items-center gap-3 px-4 py-3 sm:flex-row">
    {#if !$whisperStore.isRecording}
      <button 
        on:click={startRecording}
        disabled={$whisperStore.status === 'requesting_permission'}
        class="flex items-center justify-center px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed font-medium text-sm shadow-sm transition-all duration-200 hover:shadow"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        Start Recording
      </button>
    {:else}
      <button 
        on:click={stopRecording}
        class="flex items-center justify-center px-4 py-2.5 rounded-lg bg-gradient-to-r from-red-600 to-rose-600 text-white hover:from-red-700 hover:to-rose-700 font-medium text-sm shadow-sm transition-all duration-200 hover:shadow relative"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
        </svg>
        Stop Recording
        {#if pulseAnimation}
          <span class="absolute -top-1 -right-1 flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
        {/if}
      </button>
    {/if}
    
    <div class="flex items-center flex-1 gap-3">
      <div class="flex items-center gap-2">
        <!-- Status indicator with enhanced styling -->
        <div class={`h-4 w-4 rounded-full ${statusColor} ${pulseAnimation ? 'animate-pulse' : ''} ring-2 ring-opacity-50 ${$whisperStore.status === 'recording' ? 'ring-red-300' : 'ring-gray-200 dark:ring-gray-700'}`}></div>
        
        <!-- Status label with better visibility -->
        <span class="text-sm font-medium text-gray-700 dark:text-gray-200 capitalize">
          {#if $whisperStore.status === 'requesting_permission'}
            <span class="inline-flex items-center">
              Requesting Mic Access
              <span class="ml-1 inline-block w-4 text-center overflow-hidden">
                <span class="animate-bounce inline-block">.</span>
              </span>
            </span>
          {:else if $whisperStore.status === 'transcribing'}
            <span class="inline-flex items-center text-amber-600 dark:text-amber-400">
              Processing Audio
              <span class="ml-1 inline-block w-5 text-center overflow-hidden">
                <span class="inline-block animate-pulse">...</span>
              </span>
            </span>
          {:else if $whisperStore.status === 'analyzing'}
            <span class="inline-flex items-center text-blue-600 dark:text-blue-400">
              Analyzing Speech
              <span class="ml-1 inline-block w-5 text-center overflow-hidden">
                <span class="inline-block animate-pulse">...</span>
              </span>
            </span>
          {:else}
            {$whisperStore.status}
          {/if}
        </span>
      </div>
      
      <!-- Enhanced volume indicator (only shown when recording) -->
      {#if $whisperStore.isRecording}
        <div class="hidden sm:flex items-end h-8 gap-0.5 ml-2 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-md">
          {#each Array(5) as _, i}
            <div 
              style={`height: ${Math.max(4, Math.round($whisperStore.volumeLevel * 24 * (1 + 0.2 * (i % 3))))}px;`} 
              class="w-1.5 rounded-sm transition-all duration-75"
              class:bg-green-500={$whisperStore.volumeLevel > 0.6}
              class:bg-blue-500={$whisperStore.volumeLevel <= 0.6 && $whisperStore.volumeLevel > 0.2}
              class:bg-gray-400={$whisperStore.volumeLevel <= 0.2}
            ></div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  
  <!-- Error Message -->
  {#if $whisperStore.errorMessage}
    <div 
      class="mx-4 mb-3 p-3 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-900/50 rounded-lg text-red-800 dark:text-red-300 text-sm animate-fadeIn"
    >
      <div class="flex items-center">
        <svg class="w-5 h-5 mr-2 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12" y2="16"></line>
        </svg>
        <span>{$whisperStore.errorMessage}</span>
      </div>
    </div>
  {/if}
  
  <!-- Live Transcription Area -->
  <div class="px-4 py-3 mx-4">
    <div 
      class="min-h-[60px] max-h-[100px] px-4 py-3 rounded-lg overflow-y-auto transition-all duration-300 
      bg-gradient-to-r from-white to-gray-50 dark:from-gray-800 dark:to-gray-700
      border border-gray-100 dark:border-gray-700 shadow-inner
      {$whisperStore.liveText ? 'ring-2 ring-green-500/30' : ''}"
    >
      {#if $whisperStore.liveText}
        <p class="text-gray-800 dark:text-gray-100 font-medium">{$whisperStore.liveText}</p>
      {:else if $whisperStore.isRecording}
        <div class="flex items-center">
          <div class="w-2 h-2 bg-red-500 rounded-full animate-pulse mr-2"></div>
          <p class="italic text-gray-500 dark:text-gray-400">Listening...</p>
        </div>
      {:else}
        <p class="italic text-gray-500 dark:text-gray-400 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.536a5 5 0 01.001-7.072m12.728 0a9 9 0 000 12.728M3 12l4-4V9a3 3 0 013-3v0a3 3 0 013 3v6a3 3 0 01-3 3v0a3 3 0 01-3-3v-1l-4-4z" />
          </svg>
          Start recording to see live transcription
        </p>
      {/if}
    </div>
  </div>
  
  <!-- Conversation History - Improved to be more like conversation panel -->
  <div class="flex-1 mt-1 px-4 overflow-hidden relative">
    <div 
      bind:this={transcriptionHistoryEl}
      class="h-full overflow-y-auto pr-2 space-y-4 pb-4"
    >
      {#each $whisperStore.messages as message (message.id)}
        <div class="animate-fadeIn transition-all duration-300">
          <div class="flex mb-3 mt-1">
            <div class="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shadow-sm">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <div class="ml-3 bg-white dark:bg-gray-700 rounded-2xl rounded-tl-none p-4 max-w-[85%] shadow-sm border border-gray-100 dark:border-gray-600">
              <div class="text-gray-800 dark:text-gray-100 break-words text-sm leading-relaxed">
                {message.text}
              </div>
              <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
                {#if message.isQuestion}
                  <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 font-medium">
                    Question Detected
                  </span>
                {/if}
                <span class="text-xs text-gray-400 dark:text-gray-500 ml-auto">
                  {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
                </span>
              </div>
            </div>
          </div>
        </div>
      {/each}
      
      {#if $whisperStore.messages.length === 0}
        <div class="h-full flex items-center justify-center">
          <div class="text-center p-6 bg-white dark:bg-gray-800/80 rounded-xl border border-dashed border-gray-200 dark:border-gray-700 max-w-sm mx-auto">
            <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-indigo-50 to-blue-100 dark:from-indigo-900/20 dark:to-blue-900/20 flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-7 w-7 text-indigo-500 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <h3 class="mb-2 text-gray-700 dark:text-gray-200 font-medium">Start a conversation</h3>
            <p class="text-gray-500 dark:text-gray-400 text-sm">Click the record button to begin speaking. Your words will appear here as a conversation.</p>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideDown {
    from { transform: translateY(-10px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  :global(.animate-fadeIn) {
    animation: fadeIn 0.5s;
  }

  :global(.animate-slideDown) {
    animation: slideDown 0.3s ease-out;
  }
  
  :global(.animate-pulse) {
    animation: pulse 1.5s infinite;
  }
  
  @keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
  }
</style>
