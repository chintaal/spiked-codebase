/**
 * Whisper Transcription Service
 * Handles WebSocket connection for real-time Whisper-based transcription with sentence streaming
 */

import { transcriptionStore } from '../stores/transcription.js';

class WhisperTranscriptionService {
  constructor() {
    this.websocket = null;
    this.mediaRecorder = null;
    this.audioStream = null;
    this.isRecording = false;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    
    // Configuration
    this.config = {
      language: null, // auto-detect
      model: 'base', // base, small, medium, large
      sampleRate: 16000,
      channels: 1
    };
    
    // Sentence tracking
    this.sentenceBuffer = [];
    this.lastSentenceTime = Date.now();
    
    // Bind methods
    this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
    this.handleWebSocketOpen = this.handleWebSocketOpen.bind(this);
    this.handleWebSocketClose = this.handleWebSocketClose.bind(this);
    this.handleWebSocketError = this.handleWebSocketError.bind(this);
  }
  
  /**
   * Initialize and connect to Whisper WebSocket
   */
  async connect(options = {}) {
    try {
      // Update configuration
      this.config = { ...this.config, ...options };
      
      // Build WebSocket URL with query parameters
      const wsUrl = new URL('ws://localhost:8000/ws/whisper-hotmic');
      if (this.config.language) {
        wsUrl.searchParams.set('language', this.config.language);
      }
      wsUrl.searchParams.set('model', this.config.model);
      
      console.log(`Connecting to Whisper WebSocket: ${wsUrl.toString()}`);
      
      // Create WebSocket connection
      this.websocket = new WebSocket(wsUrl.toString());
      this.websocket.binaryType = 'arraybuffer';
      
      // Set up event handlers
      this.websocket.onopen = this.handleWebSocketOpen;
      this.websocket.onmessage = this.handleWebSocketMessage;
      this.websocket.onclose = this.handleWebSocketClose;
      this.websocket.onerror = this.handleWebSocketError;
      
      // Wait for connection
      await this.waitForConnection();
      
      console.log('Whisper WebSocket connected successfully');
      return true;
      
    } catch (error) {
      console.error('Failed to connect to Whisper WebSocket:', error);
      transcriptionStore.setError(`Connection failed: ${error.message}`);
      return false;
    }
  }
  
  /**
   * Wait for WebSocket connection to be established
   */
  waitForConnection() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, 10000);
      
      const checkConnection = () => {
        if (this.websocket.readyState === WebSocket.OPEN) {
          clearTimeout(timeout);
          resolve();
        } else if (this.websocket.readyState === WebSocket.CLOSED) {
          clearTimeout(timeout);
          reject(new Error('Connection failed'));
        } else {
          setTimeout(checkConnection, 100);
        }
      };
      
      checkConnection();
    });
  }
  
  /**
   * Start recording and streaming audio to Whisper
   */
  async startRecording() {
    try {
      if (this.isRecording) {
        console.log('Already recording');
        return;
      }
      
      // Get user media
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      // Create MediaRecorder for real-time audio streaming
      this.mediaRecorder = new MediaRecorder(this.audioStream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 16000
      });
      
      // Handle audio data
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
          // Convert Blob to ArrayBuffer and send
          event.data.arrayBuffer().then(arrayBuffer => {
            this.websocket.send(arrayBuffer);
          });
        }
      };
      
      // Start recording with small time slices for real-time streaming
      this.mediaRecorder.start(250); // 250ms chunks for hot mic
      this.isRecording = true;
      
      transcriptionStore.setRecording(true);
      transcriptionStore.setStatus('recording');
      
      console.log('Whisper recording started');
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      transcriptionStore.setError(`Recording failed: ${error.message}`);
    }
  }
  
  /**
   * Stop recording
   */
  stopRecording() {
    try {
      if (!this.isRecording) {
        console.log('Not recording');
        return;
      }
      
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }
      
      if (this.audioStream) {
        this.audioStream.getTracks().forEach(track => track.stop());
        this.audioStream = null;
      }
      
      // Send empty buffer to signal end of stream
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(new ArrayBuffer(0));
      }
      
      this.isRecording = false;
      transcriptionStore.setRecording(false);
      transcriptionStore.setStatus('ready');
      
      console.log('Whisper recording stopped');
      
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  }
  
  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    try {
      this.stopRecording();
      
      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }
      
      this.isConnected = false;
      transcriptionStore.setConnected(false);
      transcriptionStore.setStatus('disconnected');
      
      console.log('Whisper WebSocket disconnected');
      
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
  }
  
  /**
   * Handle WebSocket open event
   */
  handleWebSocketOpen() {
    console.log('Whisper WebSocket connection opened');
    this.isConnected = true;
    this.reconnectAttempts = 0;
    transcriptionStore.setConnected(true);
    transcriptionStore.setStatus('connected');
  }
  
  /**
   * Handle WebSocket message event
   */
  handleWebSocketMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'connection':
        case 'hotmic_ready':
          console.log('Whisper service ready:', data.message);
          transcriptionStore.setStatus('ready');
          break;
          
        case 'partial':
          // Update live text for partial transcriptions
          if (data && typeof data.text === 'string') {
            transcriptionStore.updateLiveText(data.text);
          } else {
            console.warn('Invalid partial transcription data:', data);
          }
          break;
          
        case 'sentence':
          // Handle completed sentences
          this.handleSentence(data);
          break;
          
        case 'transcription':
          // Handle full transcription results
          this.handleTranscription(data);
          break;
          
        case 'error':
          console.error('Whisper transcription error:', data.message);
          transcriptionStore.setError(data.message);
          break;
          
        case 'status':
          console.log('Whisper status:', data.message);
          break;
          
        default:
          console.log('Unknown Whisper message type:', data.type, data);
      }
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error, event.data);
    }
  }
  
  /**
   * Handle individual sentences from Whisper
   */
  handleSentence(data) {
    try {
      // Validate that data has the required text property
      if (!data || typeof data.text !== 'string') {
        console.warn('Invalid sentence data received:', data);
        return;
      }
      
      const sentence = data.text.trim();
      
      if (sentence && sentence.length > 3) {
        console.log('Whisper sentence:', sentence);
        
        // Add to sentence buffer
        this.sentenceBuffer.push({
          text: sentence,
          timestamp: data.timestamp || Date.now(),
          language: data.language || 'en',
          isFinal: data.is_final || false,
          hotmic: data.hotmic || false
        });
        
        // Add to transcription store
        transcriptionStore.addMessage(sentence);
        
        // Update final text with accumulated sentences
        const allSentences = this.sentenceBuffer.map(s => s.text).join(' ');
        transcriptionStore.updateFinalText(allSentences);
        
        // Dispatch custom event for sentence completion
        this.dispatchSentenceEvent(sentence, data);
        
        this.lastSentenceTime = Date.now();
      }
    } catch (error) {
      console.error('Error processing sentence:', error, 'Data:', data);
    }
  }
  
  /**
   * Handle full transcription results
   */
  handleTranscription(data) {
    try {
      // Validate that data has the required text property
      if (!data || typeof data.text !== 'string') {
        console.warn('Invalid transcription data received:', data);
        return;
      }
      
      console.log('Full Whisper transcription:', data.text);
      
      // Update final text
      transcriptionStore.updateFinalText(data.text);
      
      // If sentences are provided, add them individually
      if (data.sentences && Array.isArray(data.sentences)) {
        data.sentences.forEach(sentence => {
          transcriptionStore.addMessage(sentence);
        });
      }
    } catch (error) {
      console.error('Error processing transcription:', error, 'Data:', data);
    }
  }
  
  /**
   * Dispatch custom event for sentence completion
   */
  dispatchSentenceEvent(sentence, data) {
    const event = new CustomEvent('whisperSentence', {
      detail: {
        text: sentence,
        language: data.language || 'en',
        timestamp: data.timestamp || Date.now(),
        isFinal: data.is_final || false,
        hotmic: data.hotmic || false
      }
    });
    
    if (typeof window !== 'undefined') {
      window.dispatchEvent(event);
    }
  }
  
  /**
   * Handle WebSocket close event
   */
  handleWebSocketClose(event) {
    console.log('Whisper WebSocket connection closed:', event.code, event.reason);
    this.isConnected = false;
    transcriptionStore.setConnected(false);
    
    if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
      // Attempt to reconnect
      console.log(`Attempting to reconnect (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})...`);
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.reconnectDelay);
    } else {
      transcriptionStore.setStatus('disconnected');
    }
  }
  
  /**
   * Handle WebSocket error event
   */
  handleWebSocketError(error) {
    console.error('Whisper WebSocket error:', error);
    transcriptionStore.setError('WebSocket connection error');
  }
  
  /**
   * Get current configuration
   */
  getConfig() {
    return { ...this.config };
  }
  
  /**
   * Update configuration
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
  }
  
  /**
   * Clear sentence buffer
   */
  clearSentenceBuffer() {
    this.sentenceBuffer = [];
  }
  
  /**
   * Get sentence buffer
   */
  getSentenceBuffer() {
    return [...this.sentenceBuffer];
  }
}

// Export singleton instance with browser check
let whisperTranscriptionService;
if (typeof window !== 'undefined') {
  whisperTranscriptionService = new WhisperTranscriptionService();
}
export { whisperTranscriptionService };

// Export class for multiple instances if needed
export { WhisperTranscriptionService };
