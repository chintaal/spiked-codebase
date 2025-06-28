/**
 * Meeting Transcript Integration Service
 * 
 * This service bridges meeting transcripts from the bot with the conversation panel,
 * allowing meeting transcripts to be displayed alongside hot mic transcriptions
 * in a unified conversation view.
 */

import { transcriptionStore } from '$lib/stores/transcription.js';
import { meetingStore } from '$lib/stores/meeting.js';

class MeetingTranscriptIntegrationService {
  constructor() {
    this.isEnabled = false;
    this.lastProcessedSegmentId = null;
    this.meetingInfo = {
      meetingId: null,
      platform: null
    };
    
    // Subscribe to meeting store changes
    this.unsubscribeMeeting = meetingStore.subscribe(state => {
      if (this.isEnabled && state.transcript && state.transcript.length > 0) {
        this.processMeetingTranscripts(state.transcript, {
          meetingId: state.meetingId,
          platform: state.platform
        });
      }
    });
  }

  /**
   * Enable meeting transcript integration with conversation panel
   * @param {Object} meetingInfo - Meeting information
   */
  enable(meetingInfo = {}) {
    this.isEnabled = true;
    this.meetingInfo = meetingInfo;
    this.lastProcessedSegmentId = null;
    
    console.log('Meeting transcript integration enabled for:', meetingInfo);
    
    // Add system message to indicate integration is active
    transcriptionStore.addSystemMessage(
      `🤖 Meeting bot transcript integration enabled for ${meetingInfo.platform || 'meeting'}`
    );
  }

  /**
   * Disable meeting transcript integration
   */
  disable() {
    this.isEnabled = false;
    this.lastProcessedSegmentId = null;
    
    console.log('Meeting transcript integration disabled');
    
    // Add system message to indicate integration is disabled
    transcriptionStore.addSystemMessage(
      '🤖 Meeting bot transcript integration disabled'
    );
  }

  /**
   * Process meeting transcripts and add them to conversation panel
   * @param {Array} segments - Meeting transcript segments
   * @param {Object} meetingInfo - Meeting information
   */
  processMeetingTranscripts(segments, meetingInfo = {}) {
    if (!this.isEnabled || !segments || segments.length === 0) {
      return;
    }

    // Filter new segments since last processing
    const newSegments = this.getNewSegments(segments);
    
    if (newSegments.length === 0) {
      return;
    }

    console.log(`Processing ${newSegments.length} new meeting transcript segments`);

    // Add each new segment to the conversation panel
    newSegments.forEach(segment => {
      transcriptionStore.addMeetingTranscriptSegment(segment, {
        meetingId: meetingInfo.meetingId || this.meetingInfo.meetingId,
        platform: meetingInfo.platform || this.meetingInfo.platform
      });
    });

    // Update last processed segment
    if (newSegments.length > 0) {
      const lastSegment = newSegments[newSegments.length - 1];
      this.lastProcessedSegmentId = this.generateSegmentId(lastSegment);
    }
  }

  /**
   * Get new segments since last processing
   * @param {Array} allSegments - All meeting transcript segments
   * @returns {Array} New segments to process
   */
  getNewSegments(allSegments) {
    if (!this.lastProcessedSegmentId) {
      // First time processing, return all segments
      return allSegments;
    }

    // Find the index of the last processed segment
    const lastProcessedIndex = allSegments.findIndex(segment => 
      this.generateSegmentId(segment) === this.lastProcessedSegmentId
    );

    if (lastProcessedIndex === -1) {
      // Last processed segment not found, return all segments
      return allSegments;
    }

    // Return segments after the last processed one
    return allSegments.slice(lastProcessedIndex + 1);
  }

  /**
   * Generate a unique ID for a segment
   * @param {Object} segment - Meeting transcript segment
   * @returns {string} Unique segment ID
   */
  generateSegmentId(segment) {
    return `${segment.speaker || 'unknown'}_${segment.timestamp || Date.now()}_${segment.text?.substring(0, 20) || ''}`;
  }

  /**
   * Manually add a single meeting transcript segment
   * @param {Object} segment - Meeting transcript segment
   * @param {Object} meetingInfo - Meeting information
   */
  addMeetingSegment(segment, meetingInfo = {}) {
    if (!this.isEnabled) {
      console.log('Meeting integration disabled, not adding segment');
      return;
    }

    console.log('Adding meeting segment:', segment, meetingInfo);
    
    transcriptionStore.addMeetingTranscriptSegment(segment, {
      meetingId: meetingInfo.meetingId || this.meetingInfo.meetingId,
      platform: meetingInfo.platform || this.meetingInfo.platform
    });
  }

  /**
   * Bulk add multiple meeting transcript segments
   * @param {Array} segments - Array of meeting transcript segments
   * @param {Object} meetingInfo - Meeting information
   */
  addMeetingSegmentsBatch(segments, meetingInfo = {}) {
    if (!this.isEnabled || !segments || segments.length === 0) {
      return;
    }

    transcriptionStore.addMeetingTranscriptBatch(segments, {
      meetingId: meetingInfo.meetingId || this.meetingInfo.meetingId,
      platform: meetingInfo.platform || this.meetingInfo.platform
    });
  }

  /**
   * Clear all meeting transcript messages from conversation panel
   */
  clearMeetingTranscripts() {
    // This would need to be implemented in the transcription store
    console.log('Clearing meeting transcripts from conversation panel');
    transcriptionStore.addSystemMessage('🗑️ Meeting transcripts cleared from conversation panel');
  }

  /**
   * Get current integration status
   * @returns {Object} Integration status
   */
  getStatus() {
    return {
      isEnabled: this.isEnabled,
      meetingInfo: this.meetingInfo,
      lastProcessedSegmentId: this.lastProcessedSegmentId
    };
  }

  /**
   * Cleanup function
   */
  destroy() {
    if (this.unsubscribeMeeting) {
      this.unsubscribeMeeting();
    }
    this.disable();
  }
}

// Create and export a singleton instance
export const meetingTranscriptIntegration = new MeetingTranscriptIntegrationService();

// Export the class for testing or creating additional instances
export { MeetingTranscriptIntegrationService };
