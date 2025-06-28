import { writable, derived } from 'svelte/store';

// Meeting state store
export const meetingStore = writable({
  // Current meeting state
  currentMeeting: null,
  isConnected: false,
  isLoading: false,
  error: null,
  
  // Meeting metadata
  meetingId: '',
  platform: 'google_meet',
  botName: 'Spiked AI Bot',
  language: 'en',
  
  // Transcript data
  transcript: [],
  lastUpdated: null,
  
  // Bot status
  botStatus: 'idle', // idle, requesting, active, stopping, stopped, error
  botDetails: null,
  
  // Meetings history
  meetings: [],
  
  // UI state
  isTranscriptPolling: false,
  autoScroll: true,
  showSpeakerNames: true,
  
  // Webhook configuration
  webhookUrl: null
});

// Derived stores for easier component access
export const currentMeeting = derived(meetingStore, $store => $store.currentMeeting);
export const transcript = derived(meetingStore, $store => $store.transcript);
export const botStatus = derived(meetingStore, $store => $store.botStatus);
export const isConnected = derived(meetingStore, $store => $store.isConnected);

// Actions
export const meetingActions = {
  // Set meeting ID and platform
  setMeetingDetails: (meetingId, platform = 'google_meet') => {
    meetingStore.update(state => ({
      ...state,
      meetingId,
      platform
    }));
  },
  
  // Set bot configuration
  setBotConfig: (botName, language = 'en') => {
    meetingStore.update(state => ({
      ...state,
      botName,
      language
    }));
  },
  
  // Set loading state
  setLoading: (isLoading) => {
    meetingStore.update(state => ({
      ...state,
      isLoading
    }));
  },
  
  // Set error
  setError: (error) => {
    meetingStore.update(state => ({
      ...state,
      error,
      isLoading: false
    }));
  },
  
  // Clear error
  clearError: () => {
    meetingStore.update(state => ({
      ...state,
      error: null
    }));
  },
  
  // Set bot status
  setBotStatus: (status, details = null) => {
    meetingStore.update(state => ({
      ...state,
      botStatus: status,
      botDetails: details,
      isConnected: status === 'active'
    }));
  },
  
  // Set current meeting
  setCurrentMeeting: (meeting) => {
    meetingStore.update(state => ({
      ...state,
      currentMeeting: meeting,
      isConnected: meeting ? true : false
    }));
  },
  
  // Update transcript
  updateTranscript: (transcript) => {
    meetingStore.update(state => ({
      ...state,
      transcript,
      lastUpdated: Date.now()
    }));
  },
  
  // Add transcript segment
  addTranscriptSegment: (segment) => {
    meetingStore.update(state => ({
      ...state,
      transcript: [...state.transcript, segment],
      lastUpdated: Date.now()
    }));
  },
  
  // Set meetings history
  setMeetings: (meetings) => {
    meetingStore.update(state => ({
      ...state,
      meetings
    }));
  },
  
  // Set transcript polling state
  setTranscriptPolling: (isPolling) => {
    meetingStore.update(state => ({
      ...state,
      isTranscriptPolling: isPolling
    }));
  },
  
  // Toggle auto scroll
  toggleAutoScroll: () => {
    meetingStore.update(state => ({
      ...state,
      autoScroll: !state.autoScroll
    }));
  },
  
  // Toggle speaker names
  toggleSpeakerNames: () => {
    meetingStore.update(state => ({
      ...state,
      showSpeakerNames: !state.showSpeakerNames
    }));
  },
  
  // Reset meeting state
  reset: () => {
    meetingStore.set({
      currentMeeting: null,
      isConnected: false,
      isLoading: false,
      error: null,
      meetingId: '',
      platform: 'google_meet',
      botName: 'Spiked AI Bot',
      language: 'en',
      transcript: [],
      lastUpdated: null,
      botStatus: 'idle',
      botDetails: null,
      meetings: [],
      isTranscriptPolling: false,
      autoScroll: true,
      showSpeakerNames: true,
      webhookUrl: null
    });
  }
};

// Utility functions
export const meetingUtils = {
  // Extract meeting ID from Google Meet URL
  extractMeetingId: (url) => {
    const regex = /meet\.google\.com\/([a-z0-9-]+)/i;
    const match = url.match(regex);
    return match ? match[1] : null;
  },
  
  // Format meeting duration
  formatDuration: (startTime, endTime = null) => {
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = end - start;
    
    const hours = Math.floor(duration / (1000 * 60 * 60));
    const minutes = Math.floor((duration % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  },
  
  // Format transcript for display
  formatTranscript: (transcript) => {
    return transcript.map(segment => ({
      ...segment,
      formattedTime: new Date(segment.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    }));
  },
  
  // Group transcript by speaker
  groupBySpeaker: (transcript) => {
    const grouped = [];
    let currentGroup = null;
    
    transcript.forEach(segment => {
      if (!currentGroup || currentGroup.speaker !== segment.speaker) {
        currentGroup = {
          speaker: segment.speaker,
          segments: [segment],
          startTime: segment.timestamp,
          endTime: segment.timestamp
        };
        grouped.push(currentGroup);
      } else {
        currentGroup.segments.push(segment);
        currentGroup.endTime = segment.timestamp;
      }
    });
    
    return grouped;
  }
};
