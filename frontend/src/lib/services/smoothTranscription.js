/**
 * Ultra-Smooth Live Transcription Service
 * Inspired by ScamShield's approach - focused purely on speech-to-text conversion
 * with real-time processing and visual feedback
 */

class SmoothTranscriptionService {
  constructor() {
    // Core components
    this.recognition = null;
    this.audioStream = null;
    this.audioContext = null;
    this.analyser = null;
    this.isActive = false;
    this.isListening = false;
    
    // Transcription state
    this.currentTranscription = '';
    this.finalTranscripts = [];
    this.interimTranscript = '';
    this.lastResultIndex = 0;
    
    // Audio analysis
    this.volumeLevel = 0;
    this.isSpeaking = false;
    this.silenceStart = null;
    this.silenceThreshold = 1000; // ms
    
    // Event callbacks
    this.callbacks = {
      onTranscriptUpdate: null,
      onInterimUpdate: null,
      onVolumeUpdate: null,
      onStatusChange: null,
      onError: null
    };
    
    // Configuration optimized for smoothness
    this.config = {
      language: 'en-US',
      continuous: true,
      interimResults: true,
      maxAlternatives: 1,
      
      // Audio settings for best quality
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 44100,
        channelCount: 1
      },
      
      // UI feedback settings
      volumeUpdateInterval: 50, // ms
      smoothingFactor: 0.8,
      volumeThreshold: 0.01,
      
      // Performance settings
      restartOnSilence: true,
      restartDelay: 3000, // ms
      autoRestart: true
    };
    
    // Bind methods
    this.handleResult = this.handleResult.bind(this);
    this.handleError = this.handleError.bind(this);
    this.handleStart = this.handleStart.bind(this);
    this.handleEnd = this.handleEnd.bind(this);
    this.analyzeAudio = this.analyzeAudio.bind(this);
  }
  
  /**
   * Initialize the transcription service
   */
  async initialize() {
    try {
      console.log('Initializing Smooth Transcription Service...');
      
      // Check browser support
      if (!this.checkSupport()) {
        throw new Error('Browser does not support required APIs');
      }
      
      // Initialize Web Speech API
      await this.initializeSpeechRecognition();
      
      // Initialize audio analysis
      await this.initializeAudioAnalysis();
      
      this.isActive = true;
      this.notifyStatusChange('ready');
      
      console.log('Smooth Transcription Service initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize transcription service:', error);
      this.notifyError(`Initialization failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Check browser support for required APIs
   */
  checkSupport() {
    const hasUserMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    const hasSpeechRecognition = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    const hasAudioContext = !!(window.AudioContext || window.webkitAudioContext);
    
    console.log('Browser support check:', {
      mediaDevices: hasUserMedia,
      speechRecognition: hasSpeechRecognition,
      audioContext: hasAudioContext
    });
    
    return hasUserMedia && hasSpeechRecognition && hasAudioContext;
  }
  
  /**
   * Initialize Web Speech Recognition with optimal settings
   */
  async initializeSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      throw new Error('Web Speech API not supported');
    }
    
    this.recognition = new SpeechRecognition();
    
    // Configure for smoothest experience
    this.recognition.continuous = this.config.continuous;
    this.recognition.interimResults = this.config.interimResults;
    this.recognition.lang = this.config.language;
    this.recognition.maxAlternatives = this.config.maxAlternatives;
    
    // Event handlers
    this.recognition.onresult = this.handleResult;
    this.recognition.onerror = this.handleError;
    this.recognition.onstart = this.handleStart;
    this.recognition.onend = this.handleEnd;
    
    console.log('Speech recognition initialized with config:', {
      language: this.config.language,
      continuous: this.config.continuous,
      interimResults: this.config.interimResults
    });
  }
  
  /**
   * Initialize audio analysis for volume detection and visual feedback
   */
  async initializeAudioAnalysis() {
    try {
      // Get microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: this.config.audio
      });
      
      // Create audio context
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContext();
      
      // Create analyser
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = this.config.smoothingFactor;
      
      // Connect microphone to analyser
      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      source.connect(this.analyser);
      
      console.log('Audio analysis initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize audio analysis:', error);
      throw new Error(`Microphone access denied: ${error.message}`);
    }
  }
  
  /**
   * Start live transcription
   */
  async startTranscription() {
    if (!this.isActive) {
      throw new Error('Service not initialized');
    }
    
    if (this.isListening) {
      console.log('Transcription already active');
      return;
    }
    
    try {
      console.log('Starting live transcription...');
      
      // Resume audio context if suspended
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      
      // Reset state
      this.currentTranscription = '';
      this.interimTranscript = '';
      this.finalTranscripts = [];
      this.lastResultIndex = 0;
      
      // Start speech recognition
      this.recognition.start();
      
      // Start audio analysis
      this.startAudioAnalysis();
      
      this.isListening = true;
      this.notifyStatusChange('listening');
      
      console.log('Live transcription started successfully');
      
    } catch (error) {
      console.error('Failed to start transcription:', error);
      this.notifyError(`Failed to start: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Stop live transcription
   */
  stopTranscription() {
    if (!this.isListening) {
      return;
    }
    
    console.log('Stopping live transcription...');
    
    try {
      // Stop speech recognition
      if (this.recognition) {
        this.recognition.stop();
      }
      
      // Stop audio analysis
      this.stopAudioAnalysis();
      
      this.isListening = false;
      this.isSpeaking = false;
      this.volumeLevel = 0;
      
      this.notifyStatusChange('stopped');
      this.notifyVolumeUpdate(0);
      
      console.log('Live transcription stopped');
      
    } catch (error) {
      console.error('Error stopping transcription:', error);
    }
  }
  
  /**
   * Handle speech recognition results
   */
  handleResult(event) {
    let finalTranscript = '';
    let interimTranscript = '';
    
    // Process all results from the last processed index
    for (let i = this.lastResultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const transcript = result[0].transcript;
      
      if (result.isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }
    
    // Update state
    if (finalTranscript) {
      const transcriptEntry = {
        id: Date.now() + Math.random(),
        timestamp: new Date().toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        }),
        text: finalTranscript.trim(),
        speaker: 'Live Audio',
        type: 'final'
      };
      
      this.finalTranscripts.push(transcriptEntry);
      this.lastResultIndex = event.results.length;
      
      // Notify listeners
      this.notifyTranscriptUpdate(transcriptEntry);
      
      console.log('Final transcript:', finalTranscript);
    }
    
    if (interimTranscript) {
      this.interimTranscript = interimTranscript.trim();
      this.currentTranscription = this.interimTranscript;
      
      // Notify listeners of interim results
      this.notifyInterimUpdate(this.interimTranscript);
      
      // console.log('Interim transcript:', interimTranscript);
    }
  }
  
  /**
   * Handle speech recognition errors
   */
  handleError(event) {
    console.error('Speech recognition error:', event.error);
    
    // Handle different error types
    switch (event.error) {
      case 'no-speech':
        // Don't treat no-speech as a critical error
        if (this.config.autoRestart) {
          setTimeout(() => {
            if (this.isListening) {
              this.restartRecognition();
            }
          }, 1000);
        }
        break;
        
      case 'audio-capture':
        this.notifyError('Microphone access lost');
        this.stopTranscription();
        break;
        
      case 'not-allowed':
        this.notifyError('Microphone permission denied');
        this.stopTranscription();
        break;
        
      case 'network':
        this.notifyError('Network error - check connection');
        if (this.config.autoRestart) {
          setTimeout(() => {
            if (this.isListening) {
              this.restartRecognition();
            }
          }, 2000);
        }
        break;
        
      default:
        this.notifyError(`Recognition error: ${event.error}`);
        if (this.config.autoRestart) {
          setTimeout(() => {
            if (this.isListening) {
              this.restartRecognition();
            }
          }, 1000);
        }
    }
  }
  
  /**
   * Handle recognition start
   */
  handleStart() {
    console.log('Speech recognition started');
    this.notifyStatusChange('listening');
  }
  
  /**
   * Handle recognition end
   */
  handleEnd() {
    console.log('Speech recognition ended');
    
    if (this.isListening && this.config.autoRestart) {
      // Auto-restart to maintain continuous listening
      setTimeout(() => {
        if (this.isListening) {
          this.restartRecognition();
        }
      }, 100);
    }
  }
  
  /**
   * Restart speech recognition
   */
  restartRecognition() {
    try {
      if (this.recognition && this.isListening) {
        this.recognition.start();
      }
    } catch (error) {
      console.error('Error restarting recognition:', error);
    }
  }
  
  /**
   * Start audio analysis for volume feedback
   */
  startAudioAnalysis() {
    if (!this.analyser) return;
    
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const analyze = () => {
      if (!this.isListening) return;
      
      this.analyser.getByteFrequencyData(dataArray);
      
      // Calculate volume level
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i];
      }
      
      const average = sum / bufferLength;
      this.volumeLevel = average / 255; // Normalize to 0-1
      
      // Determine if speaking
      const wasSpeaking = this.isSpeaking;
      this.isSpeaking = this.volumeLevel > this.config.volumeThreshold;
      
      // Handle silence detection
      if (!this.isSpeaking) {
        if (wasSpeaking) {
          this.silenceStart = Date.now();
        }
      } else {
        this.silenceStart = null;
      }
      
      // Notify volume update
      this.notifyVolumeUpdate(this.volumeLevel);
      
      // Continue analysis
      requestAnimationFrame(analyze);
    };
    
    // Start the analysis loop
    requestAnimationFrame(analyze);
  }
  
  /**
   * Stop audio analysis
   */
  stopAudioAnalysis() {
    // Analysis will stop automatically when isListening becomes false
    this.volumeLevel = 0;
    this.isSpeaking = false;
  }
  
  /**
   * Set event callbacks
   */
  setCallbacks(callbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }
  
  /**
   * Notify transcript update
   */
  notifyTranscriptUpdate(transcript) {
    if (this.callbacks.onTranscriptUpdate) {
      this.callbacks.onTranscriptUpdate(transcript);
    }
  }
  
  /**
   * Notify interim update
   */
  notifyInterimUpdate(text) {
    if (this.callbacks.onInterimUpdate) {
      this.callbacks.onInterimUpdate(text);
    }
  }
  
  /**
   * Notify volume update
   */
  notifyVolumeUpdate(level) {
    if (this.callbacks.onVolumeUpdate) {
      this.callbacks.onVolumeUpdate(level);
    }
  }
  
  /**
   * Notify status change
   */
  notifyStatusChange(status) {
    if (this.callbacks.onStatusChange) {
      this.callbacks.onStatusChange(status);
    }
  }
  
  /**
   * Notify error
   */
  notifyError(error) {
    if (this.callbacks.onError) {
      this.callbacks.onError(error);
    }
  }
  
  /**
   * Get current state
   */
  getState() {
    return {
      isActive: this.isActive,
      isListening: this.isListening,
      isSpeaking: this.isSpeaking,
      volumeLevel: this.volumeLevel,
      currentTranscription: this.currentTranscription,
      interimTranscript: this.interimTranscript,
      finalTranscripts: this.finalTranscripts
    };
  }
  
  /**
   * Cleanup resources
   */
  cleanup() {
    console.log('Cleaning up Smooth Transcription Service...');
    
    // Stop transcription
    this.stopTranscription();
    
    // Close audio stream
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
    
    // Close audio context
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    
    // Clear recognition
    this.recognition = null;
    this.analyser = null;
    
    // Reset state
    this.isActive = false;
    this.isListening = false;
    this.isSpeaking = false;
    this.volumeLevel = 0;
    
    console.log('Smooth Transcription Service cleaned up');
  }
}

// Create and export singleton instance
export const smoothTranscriptionService = new SmoothTranscriptionService();
