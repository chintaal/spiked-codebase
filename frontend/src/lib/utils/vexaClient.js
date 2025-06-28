/**
 * Vexa API client for frontend
 * Handles all communication with Vexa.ai API through the backend
 */

const VEXA_BASE_URL = 'http://localhost:8000/vexa'; // Backend proxy endpoint

class VexaClient {
  constructor() {
    this.baseUrl = VEXA_BASE_URL;
  }

  // Helper method for making API requests
  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    };

    const requestOptions = {
      ...defaultOptions,
      ...options
    };

    try {
      const response = await fetch(url, requestOptions);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific error cases
        if (response.status === 409) {
          if (errorData.message && errorData.message.includes('concurrent')) {
            throw new Error('You have reached your concurrent bot limit. Please stop an existing bot first.');
          } else if (errorData.message && errorData.message.includes('already exists')) {
            throw new Error('A bot is already active for this meeting. Please stop it first or use a different meeting.');
          } else {
            throw new Error('Conflict: ' + (errorData.message || 'Another bot may already be running for this meeting.'));
          }
        }
        
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Vexa API request failed:', error);
      throw error;
    }
  }

  // Request a bot for a meeting
  async requestBot(meetingId, platform = 'google_meet', options = {}) {
    const payload = {
      platform,
      native_meeting_id: meetingId,
      language: options.language || 'en',
      bot_name: options.bot_name || 'Spiked AI Bot'
    };

    return await this.makeRequest('/bots', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // Get real-time meeting transcript
  async getTranscript(meetingId, platform = 'google_meet') {
    return await this.makeRequest(`/transcripts/${platform}/${meetingId}`);
  }

  // Get status of running bots
  async getBotStatus() {
    return await this.makeRequest('/bots/status');
  }

  // Update bot configuration
  async updateBotConfig(meetingId, platform = 'google_meet', config = {}) {
    return await this.makeRequest(`/bots/${platform}/${meetingId}/config`, {
      method: 'PUT',
      body: JSON.stringify(config)
    });
  }

  // Stop a bot
  async stopBot(meetingId, platform = 'google_meet') {
    return await this.makeRequest(`/bots/${platform}/${meetingId}`, {
      method: 'DELETE'
    });
  }

  // Stop all running bots (useful for clearing conflicts)
  async stopAllBots() {
    try {
      const statusResult = await this.getBotStatus();
      const runningBots = statusResult.running_bots || [];
      
      const stopPromises = runningBots.map(bot => {
        const platform = bot.platform || 'google_meet';
        const meetingId = bot.native_meeting_id;
        if (meetingId) {
          return this.stopBot(meetingId, platform);
        }
        return Promise.resolve();
      });
      
      await Promise.all(stopPromises);
      return { success: true, stoppedCount: runningBots.length };
    } catch (error) {
      throw new Error(`Failed to stop running bots: ${error.message}`);
    }
  }

  // List meetings
  async listMeetings() {
    return await this.makeRequest('/meetings');
  }

  // Update meeting data
  async updateMeeting(meetingId, platform = 'google_meet', data = {}) {
    const payload = { data };
    return await this.makeRequest(`/meetings/${platform}/${meetingId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  }

  // Delete meeting and transcripts
  async deleteMeeting(meetingId, platform = 'google_meet') {
    return await this.makeRequest(`/meetings/${platform}/${meetingId}`, {
      method: 'DELETE'
    });
  }

  // Set webhook URL
  async setWebhook(webhookUrl) {
    return await this.makeRequest('/user/webhook', {
      method: 'PUT',
      body: JSON.stringify({ webhook_url: webhookUrl })
    });
  }

  // Poll for transcript updates
  async startTranscriptPolling(meetingId, platform = 'google_meet', callback, interval = 3000) {
    const pollId = setInterval(async () => {
      try {
        const transcript = await this.getTranscript(meetingId, platform);
        callback(transcript);
      } catch (error) {
        console.error('Error polling transcript:', error);
        // Don't stop polling on error, just log it
      }
    }, interval);

    return pollId;
  }

  // Stop transcript polling
  stopTranscriptPolling(pollId) {
    if (pollId) {
      clearInterval(pollId);
    }
  }

  // Utility method to validate meeting URLs
  static validateMeetingUrl(url) {
    const googleMeetRegex = /meet\.google\.com\/([a-z0-9-]+)/i;
    const match = url.match(googleMeetRegex);
    
    if (match) {
      return {
        platform: 'google_meet',
        meetingId: match[1],
        isValid: true
      };
    }

    return {
      platform: null,
      meetingId: null,
      isValid: false
    };
  }

  // Utility method to extract meeting ID from URL
  static extractMeetingId(url) {
    const validation = VexaClient.validateMeetingUrl(url);
    return validation.isValid ? validation.meetingId : null;
  }
}

// Export singleton instance
export const vexaClient = new VexaClient();
export default vexaClient;
