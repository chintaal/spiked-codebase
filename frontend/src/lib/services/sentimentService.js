/**
 * Sentiment Analysis Service
 * Handles interaction with the sentiment analysis API
 */

const API_URL = 'http://localhost:8000';

/**
 * Analyze text sentiment
 * @param {string} text - The text to analyze
 * @returns {Promise<Object>} - The sentiment analysis result
 */
export async function analyzeSentiment(text) {
  try {
    const response = await fetch(`${API_URL}/analyze-sentiment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new Error(`Sentiment analysis failed with status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error analyzing sentiment:', error);
    return {
      sentiment: 'unknown',
      summary: 'Error analyzing sentiment. Please try again later.',
      success: false,
      error: error.message
    };
  }
}
