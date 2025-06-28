/**
 * Enhanced Live Transcription Service
 * Combines Web Speech API and Whisper for optimal performance and reliability
 */

import { transcriptionStore } from '../stores/transcription.js';

class EnhancedTranscriptionService {
  constructor() {
    // Core state
    this.isActive = false;
    this.currentMethod = null; // 'webspeech' | 'whisper' | 'hybrid'
    this.websocket = null;
    this.recognition = null;
    this.mediaRecorder = null;
    this.audioStream = null;
    
    // Audio processing
    this.audioContext = null;
    this.analyser = null;
    this.processor = null;
    this.volumeLevel = 0;
    this.silenceDetector = null;
    
    // Transcription buffers
    this.liveBuffer = '';
    this.finalBuffer = '';
    this.partialResults = [];
    this.lastActivityTime = Date.now();
    
    // Configuration
    this.config = {
      // Audio settings
      sampleRate: 48000,
      channels: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      
      // Transcription settings
      language: 'en-US',
      interimResults: true,
      continuous: true,
      maxAlternatives: 1,
      
      // Performance settings
      silenceThreshold: 1000, // ms
      processInterval: 100, // ms
      bufferSize: 2048,
      
      // Whisper settings
      whisperModel: 'base',
      chunkDuration: 250, // ms
      
      // UI settings
      showVolume: true,
      showInterim: true,
      autoScroll: true
    };
    
    // Bind methods
    this.handleAudioProcess = this.handleAudioProcess.bind(this);
    this.handleSpeechResult = this.handleSpeechResult.bind(this);
    this.handleSpeechError = this.handleSpeechError.bind(this);
    this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
  }
  
  /**
   * Initialize the transcription service
   */
  async initialize(method = 'hybrid', config = {}) {
    try {
      // Update configuration
      this.config = { ...this.config, ...config };
      this.currentMethod = method;
      
      console.log(`Initializing Enhanced Transcription Service with method: ${method}`);
      
      // Check browser support
      await this.checkBrowserSupport();
      
      // Initialize audio context
      await this.initializeAudioContext();
      
      // Setup chosen method
      switch (method) {
        case 'webspeech':
          await this.setupWebSpeech();
          break;
        case 'whisper':
          await this.setupWhisper();
          break;
        case 'hybrid':
          await this.setupHybrid();
          break;
        default:
          throw new Error(`Unknown transcription method: ${method}`);
      }
      
      transcriptionStore.setStatus('ready');
      console.log('Enhanced Transcription Service initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize transcription service:', error);
      transcriptionStore.setError(`Initialization failed: ${error.message}`);
      throw error;
    }
  }
  
  /**
   * Check browser support for required APIs
   */
  async checkBrowserSupport() {
    const support = {
      mediaDevices: !!navigator.mediaDevices?.getUserMedia,
      speechRecognition: !!(window.SpeechRecognition || window.webkitSpeechRecognition),
      audioContext: !!(window.AudioContext || window.webkitAudioContext),
      mediaRecorder: !!window.MediaRecorder,
      webSocket: !!window.WebSocket
    };
    
    console.log('Browser support:', support);
    
    if (!support.mediaDevices) {
      throw new Error('MediaDevices API not supported');
    }
    
    if (!support.audioContext) {
      throw new Error('Web Audio API not supported');
    }
    
    return support;
  }
  
  /**
   * Initialize audio context and audio processing
   */
  async initializeAudioContext() {
    try {
      // Create audio context
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioContext();
      
      // Request microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: this.config.echoCancellation,
          noiseSuppression: this.config.noiseSuppression,
          autoGainControl: this.config.autoGainControl
        }
      });
      
      // Create audio processing chain
      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      this.analyser = this.audioContext.createAnalyser();
      
      // Configure analyser
      this.analyser.fftSize = this.config.bufferSize;
      this.analyser.smoothingTimeConstant = 0.8;
      
      // Connect audio processing chain
      source.connect(this.analyser);
      
      // Start volume monitoring
      this.startVolumeMonitoring();
      
      console.log('Audio context initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize audio context:', error);
      throw new Error(`Audio initialization failed: ${error.message}`);
    }
  }
  
  /**
   * Setup Web Speech API
   */
  async setupWebSpeech() {
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
      throw new Error('Speech Recognition API not supported');
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    
    // Configure recognition
    this.recognition.continuous = this.config.continuous;
    this.recognition.interimResults = this.config.interimResults;
    this.recognition.lang = this.config.language;
    this.recognition.maxAlternatives = this.config.maxAlternatives;
    
    // Setup event handlers
    this.recognition.onresult = this.handleSpeechResult;
    this.recognition.onerror = this.handleSpeechError;
    this.recognition.onstart = () => {
      console.log('Speech recognition started');
      transcriptionStore.setStatus('listening');
    };
    this.recognition.onend = () => {
      console.log('Speech recognition ended');
      if (this.isActive) {
        // Auto-restart if still active
        setTimeout(() => {
          if (this.isActive) {
            try {
              this.recognition.start();
            } catch (e) {
              console.warn('Failed to restart recognition:', e);
            }
          }
        }, 100);
      } else {
        transcriptionStore.setStatus('ready');
      }
    };
    
    console.log('Web Speech API setup complete');
  }
  
  /**
   * Setup Whisper WebSocket connection
   */
  async setupWhisper() {
    try {
      const wsUrl = `ws://localhost:8000/ws/enhanced-transcribe`;
      console.log(`Connecting to Enhanced Whisper WebSocket: ${wsUrl}`);
      
      this.websocket = new WebSocket(wsUrl);
      this.websocket.binaryType = 'arraybuffer';
      
      // Setup event handlers
      this.websocket.onopen = () => {
        console.log('Enhanced Whisper WebSocket connected');
        transcriptionStore.setStatus('connected');
      };
      
      this.websocket.onmessage = this.handleWebSocketMessage;
      
      this.websocket.onclose = (event) => {
        console.log('Enhanced Whisper WebSocket closed:', event.code, event.reason);
        if (this.isActive) {
          this.attemptReconnection();
        }
      };
      
      this.websocket.onerror = (error) => {
        console.error('Enhanced Whisper WebSocket error:', error);
        transcriptionStore.setError('WebSocket connection error');
      };
      
      // Wait for connection
      await this.waitForConnection();
      
      // Setup media recorder for audio streaming
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      });
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.websocket?.readyState === WebSocket.OPEN) {
          event.data.arrayBuffer().then(buffer => {
            this.websocket.send(buffer);
          });
        }
      };
      
      console.log('Enhanced Whisper setup complete');
      
    } catch (error) {
      console.error('Failed to setup Enhanced Whisper:', error);
      throw error;
    }
  }
  
  /**
   * Setup hybrid mode (Web Speech + Whisper fallback)
   */
  async setupHybrid() {
    try {
      // Try Web Speech first (faster)
      await this.setupWebSpeech();
      
      // Setup Whisper as fallback
      try {
        await this.setupWhisper();
        console.log('Hybrid mode: Both Web Speech and Whisper available');
      } catch (error) {
        console.warn('Whisper not available, using Web Speech only:', error);
      }
      
    } catch (error) {
      // If Web Speech fails, try Whisper only
      console.warn('Web Speech not available, trying Whisper only:', error);
      await this.setupWhisper();
    }
  }
  
  /**
   * Start live transcription
   */
  async startTranscription() {
    try {
      if (this.isActive) {
        console.log('Transcription already active');
        return;
      }
      
      this.isActive = true;
      this.clearBuffers();
      
      transcriptionStore.setRecording(true);
      transcriptionStore.setStatus('starting');
      
      // Resume audio context if needed
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      
      // Start chosen method
      switch (this.currentMethod) {
        case 'webspeech':
          this.recognition.start();
          break;
        case 'whisper':
          this.mediaRecorder.start(this.config.chunkDuration);
          break;
        case 'hybrid':
          // Start both
          this.recognition.start();
          if (this.mediaRecorder) {
            this.mediaRecorder.start(this.config.chunkDuration);
          }
          break;
      }
      
      console.log('Live transcription started');
      
    } catch (error) {
      console.error('Failed to start transcription:', error);
      transcriptionStore.setError(`Failed to start: ${error.message}`);
      this.isActive = false;
    }
  }
  
  /**
   * Stop live transcription
   */
  async stopTranscription() {
    try {
      if (!this.isActive) {
        console.log('Transcription not active');
        return;
      }
      
      this.isActive = false;
      
      // Stop recognition
      if (this.recognition) {
        this.recognition.stop();
      }
      
      // Stop media recorder
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }
      
      // Send final text if available
      if (this.liveBuffer.trim()) {
        transcriptionStore.updateFinalText(this.liveBuffer);
        transcriptionStore.addMessage(this.liveBuffer);
      }
      
      // Stop volume monitoring
      this.stopVolumeMonitoring();
      
      transcriptionStore.setRecording(false);
      transcriptionStore.setStatus('ready');
      
      console.log('Live transcription stopped');
      
    } catch (error) {
      console.error('Error stopping transcription:', error);
    }
  }
  
  /**
   * Handle speech recognition results
   */
  handleSpeechResult(event) {
    let interimTranscript = '';
    let finalTranscript = '';
    
    // Process all results
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      const transcript = result[0].transcript;
      
      if (result.isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }
    
    // Update live text with interim results
    if (interimTranscript) {
      this.liveBuffer = interimTranscript;
      transcriptionStore.updateLiveText(interimTranscript);
    }
    
    // Handle final results
    if (finalTranscript) {
      this.finalBuffer += (this.finalBuffer ? ' ' : '') + finalTranscript;
      transcriptionStore.updateFinalText(this.finalBuffer);
      transcriptionStore.addMessage(finalTranscript);
      
      // Clear live buffer after final result
      this.liveBuffer = '';
      transcriptionStore.updateLiveText('');
    }
    
    this.lastActivityTime = Date.now();
  }
  
  /**
   * Handle speech recognition errors
   */
  handleSpeechError(event) {
    console.error('Speech recognition error:', event.error);
    
    let errorMessage = 'Speech recognition error: ';
    switch (event.error) {
      case 'not-allowed':
        errorMessage += 'Microphone access denied';
        break;
      case 'no-speech':
        errorMessage += 'No speech detected';
        break;
      case 'network':
        errorMessage += 'Network error';
        break;
      case 'audio-capture':
        errorMessage += 'Audio capture failed';
        break;
      default:
        errorMessage += event.error;
    }
    
    transcriptionStore.setError(errorMessage);
    
    // Try to recover automatically
    if (this.isActive && ['network', 'audio-capture'].includes(event.error)) {
      setTimeout(() => {
        if (this.isActive) {
          this.attemptRecovery();
        }
      }, 1000);
    }
  }
  
  /**
   * Handle WebSocket messages from Whisper
   */
  handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type || data.status) {
        case 'status':
          console.log('Enhanced transcription status:', data.text);
          transcriptionStore.setStatus(data.status || 'ready');
          break;
          
        case 'immediate':
          // Ultra-fast immediate feedback
          if (data.text && this.config.showInterim) {
            this.liveBuffer = data.text;
            transcriptionStore.updateLiveText(data.text);
          }
          break;
          
        case 'partial':
        case 'segment':
          // Real-time partial transcriptions
          if (data.text) {
            this.liveBuffer = data.text;
            transcriptionStore.updateLiveText(data.text);
            
            // Update cumulative text if available
            if (data.cumulative_text) {
              this.finalBuffer = data.cumulative_text;
              transcriptionStore.updateFinalText(data.cumulative_text);
            }
          }
          break;
          
        case 'speech_start':
          console.log('Speech detection started');
          transcriptionStore.setStatus('listening');
          break;
          
        case 'speech_end':
        case 'speech_completed':
          // Completed speech segment
          if (data.text) {
            this.finalBuffer = data.cumulative_text || data.text;
            transcriptionStore.updateFinalText(this.finalBuffer);
            transcriptionStore.addMessage(data.text);
            
            // Clear live buffer after final result
            this.liveBuffer = '';
            transcriptionStore.updateLiveText('');
          }
          break;
          
        case 'silence':
        case 'silence_detected':
          console.log('Silence detected');
          transcriptionStore.setStatus('listening');
          break;
          
        case 'final':
        case 'completed':
          // Final transcription result
          if (data.text) {
            this.finalBuffer = data.cumulative_text || data.text;
            transcriptionStore.updateFinalText(this.finalBuffer);
            transcriptionStore.addMessage(data.text);
            
            // Clear live buffer
            this.liveBuffer = '';
            transcriptionStore.updateLiveText('');
          }
          transcriptionStore.setStatus('ready');
          break;
          
        case 'error':
          console.error('Enhanced transcription error:', data.error || data.message);
          transcriptionStore.setError(data.error || data.message || 'Unknown error');
          break;
          
        default:
          console.log('Enhanced transcription message:', data);
      }
      
      this.lastActivityTime = Date.now();
      
    } catch (error) {
      console.error('Error parsing Enhanced WebSocket message:', error);
    }
  }
  
  /**
   * Start volume monitoring for visual feedback
   */
  startVolumeMonitoring() {
    if (!this.config.showVolume || !this.analyser) return;
    
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const updateVolume = () => {
      if (!this.isActive) return;
      
      this.analyser.getByteFrequencyData(dataArray);
      
      // Calculate RMS volume
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i] * dataArray[i];
      }
      const rms = Math.sqrt(sum / bufferLength);
      
      // Normalize to 0-100 range
      this.volumeLevel = Math.min(100, (rms / 255) * 100);
      transcriptionStore.setVolumeLevel(this.volumeLevel);
      
      requestAnimationFrame(updateVolume);
    };
    
    updateVolume();
  }
  
  /**
   * Stop volume monitoring
   */
  stopVolumeMonitoring() {
    transcriptionStore.setVolumeLevel(0);
  }
  
  /**
   * Wait for WebSocket connection
   */
  waitForConnection() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000);
      
      const checkConnection = () => {
        if (this.websocket.readyState === WebSocket.OPEN) {
          clearTimeout(timeout);
          resolve();
        } else if (this.websocket.readyState === WebSocket.CLOSED) {
          clearTimeout(timeout);
          reject(new Error('WebSocket connection failed'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };
      
      checkConnection();
    });
  }
  
  /**
   * Attempt to reconnect WebSocket
   */
  async attemptReconnection() {
    if (!this.isActive) return;
    
    console.log('Attempting WebSocket reconnection...');
    transcriptionStore.setStatus('reconnecting');
    
    try {
      await this.setupWhisper();
      if (this.mediaRecorder) {
        this.mediaRecorder.start(this.config.chunkDuration);
      }
      console.log('WebSocket reconnected successfully');
    } catch (error) {
      console.error('Reconnection failed:', error);
      transcriptionStore.setError('Reconnection failed');
    }
  }
  
  /**
   * Attempt to recover from errors
   */
  async attemptRecovery() {
    console.log('Attempting error recovery...');
    
    try {
      // Stop current transcription
      await this.stopTranscription();
      
      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Restart transcription
      await this.startTranscription();
      
      console.log('Recovery successful');
    } catch (error) {
      console.error('Recovery failed:', error);
      transcriptionStore.setError('Recovery failed');
    }
  }
  
  /**
   * Clear transcription buffers
   */
  clearBuffers() {
    this.liveBuffer = '';
    this.finalBuffer = '';
    this.partialResults = [];
    transcriptionStore.updateLiveText('');
    transcriptionStore.updateFinalText('');
  }
  
  /**
   * Update configuration
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
    console.log('Configuration updated:', this.config);
  }
  
  /**
   * Get current status
   */
  getStatus() {
    return {
      isActive: this.isActive,
      method: this.currentMethod,
      volumeLevel: this.volumeLevel,
      lastActivity: this.lastActivityTime,
      config: this.config
    };
  }
  
  /**
   * Cleanup resources
   */
  async cleanup() {
    try {
      // Stop transcription
      await this.stopTranscription();
      
      // Close WebSocket
      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }
      
      // Stop audio stream
      if (this.audioStream) {
        this.audioStream.getTracks().forEach(track => track.stop());
        this.audioStream = null;
      }
      
      // Close audio context
      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }
      
      console.log('Enhanced transcription service cleaned up');
      
    } catch (error) {
      console.error('Error during cleanup:', error);
    }
  }
}

// Export singleton instance
let enhancedTranscriptionService;
if (typeof window !== 'undefined') {
  enhancedTranscriptionService = new EnhancedTranscriptionService();
}

export { enhancedTranscriptionService, EnhancedTranscriptionService };
