/**
 * Service for handling API calls to OpenAI
 */

// Get API key from environment variables (set in .env file)
const OPENAI_API_KEY = import.meta.env.VITE_OPENAI_API_KEY;

/**
 * Transcribes audio using OpenAI's Whisper API
 * @param {Blob} audioBlob - Audio blob to transcribe
 * @returns {Promise<string>} - The transcribed text
 */
export async function transcribeAudio(audioBlob) {
  try {
    // First, we need to ensure we're using the right format
    // WebM can be problematic with Whisper, so let's convert to mp3 if needed
    let blobToSend = audioBlob;
    let filename = 'audio_recording.webm';
    
    // Check the audio blob MIME type
    const mimeType = audioBlob.type;
    console.log('Original audio MIME type:', mimeType);
    
    // If the mimetype is not in supported formats, the API will reject it
    // Supported: flac, m4a, mp3, mp4, mpeg, mpga, oga, ogg, wav, webm
    // But webm can be problematic if it's not properly encoded
    if (mimeType === 'audio/webm') {
      filename = 'audio_recording.webm';
    } else if (mimeType === 'audio/mp3' || mimeType === 'audio/mpeg') {
      filename = 'audio_recording.mp3';
    } else if (mimeType === 'audio/wav') {
      filename = 'audio_recording.wav';
    } else if (mimeType === 'audio/ogg') {
      filename = 'audio_recording.ogg';
    }
    
    console.log(`Sending audio as ${filename}`);
    
    const formData = new FormData();
    formData.append('file', blobToSend, filename);
    formData.append('model', 'whisper-1');
    // Add response format explicitly
    formData.append('response_format', 'json');
    // Add language hint to improve accuracy
    formData.append('language', 'en');
    
    console.log('Sending audio to Whisper API...');
    
    const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      console.error('Whisper API error:', errorData);
      
      // More informative error message
      const errorMessage = errorData?.error?.message || response.statusText || 'Unknown error';
      throw new Error(`Transcription failed: ${errorMessage}`);
    }
    
    const data = await response.json();
    console.log('Whisper API response:', data);
    return data.text || '';
  } catch (error) {
    console.error('Error transcribing audio:', error);
    throw error;
  }
}


