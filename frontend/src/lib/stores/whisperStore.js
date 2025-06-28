import { writable } from 'svelte/store';

/**
 * Creates a whisper transcription store to manage real-time transcription state
 */
function createWhisperStore() {
  const { subscribe, set, update } = writable({
    isRecording: false,
    isProcessing: false,
    isConnectedToMic: false,
    liveText: "",
    finalText: "",
    errorMessage: null,
    status: "ready", // ready, recording, processing, error
    volumeLevel: 0,
    messages: [],
    audioChunks: [],
    detectedQuestions: []
  });

  return {
    subscribe,
    
    setStatus: (status) => {
      update(state => ({ ...state, status }));
    },
    
    setRecording: (isRecording) => {
      update(state => ({ ...state, isRecording }));
    },
    
    setProcessing: (isProcessing) => {
      update(state => ({ ...state, isProcessing }));
    },
    
    setConnectedToMic: (isConnectedToMic) => {
      update(state => ({ ...state, isConnectedToMic }));
    },
    
    updateLiveText: (text) => {
      update(state => ({ ...state, liveText: text }));
    },
    
    updateFinalText: (text) => {
      update(state => ({ ...state, finalText: text }));
    },
    
    setVolumeLevel: (level) => {
      update(state => ({ ...state, volumeLevel: level }));
    },
    
    setError: (errorMessage) => {
      update(state => ({ ...state, errorMessage }));
    },
    
    addAudioChunk: (chunk) => {
      update(state => ({
        ...state,
        audioChunks: [...state.audioChunks, chunk]
      }));
    },
    
    clearAudioChunks: () => {
      update(state => ({ ...state, audioChunks: [] }));
    },
    
    addMessage: (message, isQuestion = false) => {
      // Check if it's an empty message
      if (!message || message.trim() === '') return;
      
      update(state => {
        const newMessage = {
          id: Date.now().toString(),
          text: message,
          timestamp: new Date().toISOString(),
          isQuestion
        };
        
        return {
          ...state,
          messages: [...state.messages, newMessage]
        };
      });
    },
    
    addDetectedQuestion: (question) => {
      update(state => ({
        ...state,
        detectedQuestions: [...state.detectedQuestions, {
          id: Date.now().toString(),
          text: question,
          timestamp: new Date().toISOString(),
          answered: false
        }]
      }));
    },
    
    markQuestionAsAnswered: (questionId) => {
      update(state => ({
        ...state,
        detectedQuestions: state.detectedQuestions.map(q => 
          q.id === questionId ? { ...q, answered: true } : q
        )
      }));
    },
    
    reset: () => {
      update(state => ({
        ...state,
        liveText: "",
        finalText: "",
        status: "ready",
        errorMessage: null,
        audioChunks: []
      }));
    },
    
    resetMessages: () => {
      update(state => ({
        ...state,
        messages: []
      }));
    },
    
    resetAll: () => {
      set({
        isRecording: false,
        isProcessing: false,
        isConnectedToMic: false,
        liveText: "",
        finalText: "",
        errorMessage: null,
        status: "ready",
        volumeLevel: 0,
        messages: [],
        audioChunks: [],
        detectedQuestions: []
      });
    }
  };
}

export const whisperStore = createWhisperStore();
