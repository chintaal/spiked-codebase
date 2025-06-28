/**
 * Meeting URL validation utilities
 * Provides functions for validating and extracting meeting IDs from various platforms
 */

/**
 * Extract meeting ID from a Google Meet URL
 * 
 * @param {string} url - Google Meet URL
 * @returns {string|null} - Extracted meeting ID or null if invalid
 */
export function extractGoogleMeetId(url) {
  if (!url) return null;
  
  // Common Google Meet URL patterns:
  // https://meet.google.com/abc-defg-hij
  // https://meet.google.com/lookup/abc-defg-hij
  
  try {
    // Convert to URL object and validate
    const urlObj = new URL(url);
    
    // Validate hostname
    if (!urlObj.hostname.includes('meet.google.com')) {
      // Try checking if it's just a meet code directly
      const meetCodeRegex = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i;
      if (meetCodeRegex.test(url.trim())) {
        return url.trim();
      }
      return null;
    }
    
    // Extract the pathname
    const pathParts = urlObj.pathname.split('/').filter(Boolean);
    
    // Handle different path patterns
    if (pathParts.length >= 1) {
      const lastPart = pathParts[pathParts.length - 1];
      
      // Check if it matches the typical meet code pattern (xxx-xxxx-xxx)
      const meetCodeRegex = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i;
      if (meetCodeRegex.test(lastPart)) {
        return lastPart;
      }
    }
    
    return null;
  } catch (error) {
    // If URL parsing fails, try direct pattern matching
    const meetCodeRegex = /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i;
    if (meetCodeRegex.test(url.trim())) {
      return url.trim();
    }
    return null;
  }
}

/**
 * Extract meeting ID from a Zoom URL
 * 
 * @param {string} url - Zoom meeting URL
 * @returns {string|null} - Extracted meeting ID or null if invalid
 */
export function extractZoomMeetingId(url) {
  if (!url) return null;
  
  // Common Zoom URL patterns:
  // https://zoom.us/j/1234567890
  // https://zoom.us/j/1234567890?pwd=XXXXXX
  // zoom.us/j/1234567890

  try {
    // Try to match the Zoom meeting ID pattern
    const zoomRegex = /(?:zoom\.us\/j\/|zoom\.us\/meeting\/|zoom\.us\/s\/|zoomgov\.com\/j\/)([0-9]+)/i;
    const match = url.match(zoomRegex);
    
    if (match && match[1]) {
      return match[1];
    }
    
    // Check if it's a numeric ID directly
    if (/^\d{9,}$/.test(url.trim())) {
      return url.trim();
    }
    
    return null;
  } catch (error) {
    return null;
  }
}

/**
 * Extract meeting ID from a Teams URL
 * 
 * @param {string} url - MS Teams meeting URL
 * @returns {string|null} - Extracted meeting ID or null if invalid
 */
export function extractTeamsMeetingId(url) {
  if (!url) return null;
  
  // Common Teams URL patterns:
  // https://teams.microsoft.com/l/meetup-join/meeting_id/conversation_id
  // https://teams.live.com/meet/meeting_id
  
  try {
    // Try to match the Teams meeting URL pattern to extract the meeting ID
    const teamsRegex = /(?:teams\.microsoft\.com\/l\/meetup-join|teams\.live\.com\/meet)\/([^\/\?]+)/i;
    const match = url.match(teamsRegex);
    
    if (match && match[1]) {
      return match[1];
    }
    
    return null;
  } catch (error) {
    return null;
  }
}

/**
 * Validate and extract meeting ID for the given platform
 * 
 * @param {string} url - Meeting URL
 * @param {string} platform - Platform (google_meet, zoom, teams)
 * @returns {string|null} - Extracted meeting ID or null if invalid
 */
export function validateMeetingUrl(url, platform) {
  if (!url || !platform) return null;
  
  switch (platform) {
    case 'google_meet':
      return extractGoogleMeetId(url);
    case 'zoom':
      return extractZoomMeetingId(url);
    case 'teams':
      return extractTeamsMeetingId(url);
    default:
      return null;
  }
}

/**
 * Determine meeting platform from URL
 * 
 * @param {string} url - Meeting URL
 * @returns {string|null} - Platform identifier or null if unknown
 */
export function detectPlatformFromUrl(url) {
  if (!url) return null;
  
  if (url.includes('meet.google.com') || /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i.test(url.trim())) {
    return 'google_meet';
  } else if (url.includes('zoom.us') || /^\d{9,}$/.test(url.trim())) {
    return 'zoom';
  } else if (url.includes('teams.microsoft.com') || url.includes('teams.live.com')) {
    return 'teams';
  }
  
  return null;
}
