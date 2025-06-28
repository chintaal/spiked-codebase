/**
 * Vexa API service for managing meeting bots and transcripts
 */

/**
 * Add Vexa bot to a meeting
 * 
 * @param {string} nativeMeetingId - The meeting ID from Google Meet
 * @param {string} platform - The platform (google_meet, zoom, teams)
 * @returns {Promise<Object>} - Meeting information
 */
export async function joinMeeting(nativeMeetingId, platform) {
  try {
    const response = await fetch('/api/vexa/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        native_meeting_id: nativeMeetingId,
        platform 
      })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add bot: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error in joinMeeting:', error);
    throw error;
  }
}

/**
 * Get transcripts from a meeting
 * 
 * @param {string} platform - The platform (google_meet, zoom, teams)
 * @param {string} meetingId - The meeting ID
 * @returns {Promise<Object>} - Transcript data
 */
export async function getMeetingTranscripts(platform, meetingId) {
  try {
    const response = await fetch(`/api/vexa/transcripts/${platform}/${meetingId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch transcripts: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error in getMeetingTranscripts:', error);
    throw error;
  }
}

/**
 * Remove Vexa bot from a meeting
 * 
 * @param {string} platform - The platform (google_meet, zoom, teams)
 * @param {string} meetingId - The meeting ID
 * @returns {Promise<Object>} - Status information
 */
export async function leaveMeeting(platform, meetingId) {
  try {
    const response = await fetch(`/api/vexa/leave/${platform}/${meetingId}`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      throw new Error(`Failed to remove bot: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error in leaveMeeting:', error);
    throw error;
  }
}
