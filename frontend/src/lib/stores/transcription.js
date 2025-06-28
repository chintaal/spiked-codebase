import { writable } from 'svelte/store';

/**
 * Enhanced question detection function that looks for various question patterns
 * and not just messages ending with "?"
 */
function detectQuestion(text) {
  if (!text) return false;
  
  const cleanedText = text.trim();
  
  // Check for question mark at the end
  if (cleanedText.endsWith('?')) return true;
  
  // Common question patterns
  const questionPatterns = [
    /^(what|who|when|where|why|how|can|could|would|will|should|do|does|did|is|are|am|was|were)\s/i,
    /\b(can you|could you|would you|will you|do you|can we|could we|should we)\s/i,
    /\b(tell me about|explain|elaborate on|clarify|any thoughts on|thoughts about)\s/i
  ];
  
  return questionPatterns.some(pattern => pattern.test(cleanedText));
}

function createTranscriptionStore() {
  const { subscribe, set, update } = writable({
    isRecording: false,
    isConnected: false,
    liveText: "",
    finalText: "",
    hasTranscript: false,
    status: "ready",
    errorMessage: null,
    volumeLevel: 0,
    messages: []
  });

  return {
    subscribe,
    
    setStatus: (status) => {
      update(state => ({ ...state, status }));
    },
    
    setRecording: (isRecording) => {
      update(state => ({ ...state, isRecording }));
    },
    
    setConnected: (isConnected) => {
      update(state => ({ ...state, isConnected }));
    },
    
    updateLiveText: (text) => {
      update(state => ({ 
        ...state, 
        liveText: text, 
        hasTranscript: true 
      }));
    },
    
    updateFinalText: (text) => {
      update(state => ({ 
        ...state, 
        finalText: text, 
        hasTranscript: true 
      }));
    },
    
    setVolumeLevel: (level) => {
      update(state => ({ ...state, volumeLevel: level }));
    },
    
    setError: (errorMessage) => {
      update(state => ({ ...state, errorMessage }));
    },
    
    addMessage: (message) => {
      console.log('Adding regular message:', message);
      update(state => {
        const newMessage = {
          id: Date.now().toString() + '_' + Math.random().toString(36).substr(2, 9),
          text: message,
          timestamp: new Date().toISOString(),
          isQuestion: detectQuestion(message),
          source: 'hotmic'
        };
        
        console.log('Created message object:', newMessage);
        console.log('Previous message count:', state.messages.length);
        
        const newState = {
          ...state,
          messages: [...state.messages, newMessage]
        };
        
        console.log('New message count:', newState.messages.length);
        return newState;
      });
    },
    
    addSystemMessage: (message) => {
      update(state => {
        const newMessage = {
          id: Date.now().toString(),
          text: message,
          timestamp: new Date().toISOString(),
          isQuestion: false,
          isSystem: true
        };
        
        return {
          ...state,
          messages: [...state.messages, newMessage]
        };
      });
    },
    
    addMeetingTranscriptSegment: (segment, meetingInfo = {}) => {
      console.log('addMeetingTranscriptSegment called with:', segment, meetingInfo);
      
      update(state => {
        const timestamp = segment.timestamp || segment.start_time || new Date().toISOString();
        
        // Check for duplicates
        const duplicateKey = `${timestamp}_${segment.text}`;
        const existingMessage = state.messages.find(msg => 
          msg.isMeetingTranscript && `${msg.timestamp}_${msg.text}` === duplicateKey
        );
        
        if (existingMessage) {
          console.log('Skipping duplicate meeting transcript segment');
          return state;
        }
        
        const newMessage = {
          id: `${timestamp}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          text: segment.text,
          timestamp: timestamp,
          isQuestion: detectQuestion(segment.text),
          source: 'meeting',
          speaker: segment.speaker || 'Unknown Speaker',
          confidence: segment.confidence || null,
          isSystem: false,
          meetingId: meetingInfo.meetingId || null,
          platform: meetingInfo.platform || null,
          isMeetingTranscript: true,
          startTime: segment.start_time || null,
          endTime: segment.end_time || null
        };
        
        console.log('Adding meeting transcript message:', newMessage);
        console.log('Current message count:', state.messages.length, '-> New count:', state.messages.length + 1);
        
        return {
          ...state,
          messages: [...state.messages, newMessage]
        };
      });
    },

    addMeetingTranscriptBatch: (segments, meetingInfo = {}) => {
      if (!segments || segments.length === 0) return;
      
      console.log('addMeetingTranscriptBatch called with:', segments.length, 'segments');
      
      update(state => {
        // Generate unique IDs for each segment with better deduplication
        const newMessages = segments.map((segment, index) => {
          const timestamp = segment.timestamp || segment.start_time || new Date().toISOString();
          const uniqueId = `${timestamp}_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}`;
          
          return {
            id: uniqueId,
            text: segment.text,
            timestamp: timestamp,
            isQuestion: detectQuestion(segment.text),
            source: 'meeting',
            speaker: segment.speaker || 'Unknown Speaker',
            confidence: segment.confidence || null,
            isSystem: false,
            meetingId: meetingInfo.meetingId || null,
            platform: meetingInfo.platform || null,
            isMeetingTranscript: true,
            startTime: segment.start_time || null,
            endTime: segment.end_time || null
          };
        });
        
        // Filter out potential duplicates based on text content and timestamp
        const existingTexts = new Set(
          state.messages
            .filter(msg => msg.isMeetingTranscript)
            .map(msg => `${msg.timestamp}_${msg.text}`)
        );
        
        const filteredMessages = newMessages.filter(msg => 
          !existingTexts.has(`${msg.timestamp}_${msg.text}`)
        );
        
        if (filteredMessages.length > 0) {
          console.log(`Adding ${filteredMessages.length} new meeting transcript segments to conversation`);
        }
        
        return {
          ...state,
          messages: [...state.messages, ...filteredMessages]
        };
      });
    },
    
    reset: () => {
      update(state => ({
        ...state,
        liveText: "",
        finalText: "",
        hasTranscript: false,
        status: "ready",
        errorMessage: null
      }));
    },
    
    resetMessages: () => {
      console.log('Resetting all messages');
      update(state => ({
        ...state,
        messages: []
      }));
    }
  };
}

export const transcriptionStore = createTranscriptionStore();