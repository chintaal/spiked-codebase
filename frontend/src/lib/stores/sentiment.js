import { writable } from 'svelte/store';
import { analyzeSentiment } from '$lib/services/sentimentService.js';
import { transcriptionStore } from './transcription.js';

function createSentimentStore() {
  const { subscribe, set, update } = writable({
    sentiment: 'neutral',
    summary: '',
    lastUpdated: null,
    isAnalyzing: false,
    error: null
  });
  
  let updateInterval = null;
  let combinedText = '';

  return {
    subscribe,
    
    /**
     * Start periodic sentiment analysis
     * @param {number} intervalMs - The update interval in milliseconds
     */
    startPeriodicAnalysis: (intervalMs = 5000) => {
      // Clear any existing interval
      if (updateInterval) {
        clearInterval(updateInterval);
      }
      
      // Set up a new interval to analyze sentiment periodically
      updateInterval = setInterval(async () => {
        // Get all messages from transcription store
        let transcription;
        const unsubscribe = transcriptionStore.subscribe(value => {
          transcription = value;
        });
        unsubscribe();
        
        // Check if there are any messages to analyze
        if (!transcription.messages || transcription.messages.length === 0) {
          update(state => ({
            ...state,
            summary: 'No conversation data to analyze'
          }));
          return;
        }
        
        // Combine all message texts
        const newCombinedText = transcription.messages
          .map(m => m.text)
          .join('\n');
          
        // Skip analysis if text hasn't changed
        if (newCombinedText === combinedText && combinedText !== '') {
          return;
        }
        
        combinedText = newCombinedText;
        
        // Update state to indicate analysis is in progress
        update(state => ({ ...state, isAnalyzing: true }));
        
        try {
          // Call the sentiment analysis API
          const result = await analyzeSentiment(combinedText);
          
          // Update the store with the result
          update(state => ({
            sentiment: result.sentiment || 'neutral',
            summary: result.summary || 'No sentiment data available',
            lastUpdated: new Date(),
            isAnalyzing: false,
            error: null
          }));
        } catch (error) {
          console.error('Error in sentiment analysis:', error);
          update(state => ({
            ...state,
            isAnalyzing: false,
            error: error.message || 'Error analyzing sentiment'
          }));
        }
      }, intervalMs);
    },
    
    /**
     * Stop periodic sentiment analysis
     */
    stopPeriodicAnalysis: () => {
      if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
      }
    },
    
    /**
     * Force an immediate sentiment analysis
     */
    analyzeNow: async () => {
      // Get all messages from transcription store
      let transcription;
      const unsubscribe = transcriptionStore.subscribe(value => {
        transcription = value;
      });
      unsubscribe();
      
      // Check if there are any messages to analyze
      if (!transcription.messages || transcription.messages.length === 0) {
        update(state => ({
          ...state,
          summary: 'No conversation data to analyze'
        }));
        return;
      }
      
      // Combine all message texts
      combinedText = transcription.messages
        .map(m => m.text)
        .join('\n');
        
      // Update state to indicate analysis is in progress
      update(state => ({ ...state, isAnalyzing: true }));
      
      try {
        // Call the sentiment analysis API
        const result = await analyzeSentiment(combinedText);
        
        // Update the store with the result
        update(state => ({
          sentiment: result.sentiment || 'neutral',
          summary: result.summary || 'No sentiment data available',
          lastUpdated: new Date(),
          isAnalyzing: false,
          error: null
        }));
      } catch (error) {
        console.error('Error in sentiment analysis:', error);
        update(state => ({
          ...state,
          isAnalyzing: false,
          error: error.message || 'Error analyzing sentiment'
        }));
      }
    },
    
    // Get the current state (for use within other store methods)
    getState: () => {
      let state;
      const unsubscribe = subscribe(value => {
        state = value;
      });
      unsubscribe();
      return state;
    }
  };
}

export const sentimentStore = createSentimentStore();
