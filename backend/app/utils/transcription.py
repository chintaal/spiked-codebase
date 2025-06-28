from openai import OpenAI
import asyncio
import base64
import json
import logging
import io
import os
import tempfile
import time
import threading
from typing import Dict, Any, AsyncGenerator, Optional, List
from app.config import OPENAI_API_KEY
from app.prompts import TRANSCRIPTION_SYSTEM_PROMPT, TRANSCRIPTION_FORMATTING_PROMPT
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import wave
import struct

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# Add the streaming transcription implementation
async def process_streaming_audio(audio_queue, send_to_client) -> None:
    """
    Process audio in ultra-low-latency streaming mode similar to Google Live Captions.
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
    """
    accumulated_audio = bytearray()
    temp_file_path = None
    buffer_window = bytearray()  # Rolling window of recent audio for context
    window_size = 24000  # ~1.5 seconds at 16kHz for context window
    silence_threshold = 500  # Minimum ms of silence to trigger processing
    last_speech_time = None
    current_transcript = ""
    
    try:
        # Send initial status
        await send_to_client({
            "type": "status",
            "text": "Listening...",
            "is_final": False,
            "status": "listening"
        })
        
        while True:
            try:
                # Wait for audio chunks with a short timeout
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.05)
                
                if chunk is None:  # End signal
                    # Process any remaining audio and finish
                    if accumulated_audio:
                        final_text = await transcribe_chunk(accumulated_audio)
                        if final_text:
                            await send_to_client({
                                "type": "transcription",
                                "text": final_text,
                                "is_final": True,
                                "status": "completed"
                            })
                    break
                
                # Add to accumulated audio
                accumulated_audio.extend(chunk)
                
                # Add to rolling context window, maintaining the window size
                buffer_window.extend(chunk)
                if len(buffer_window) > window_size:
                    buffer_window = buffer_window[-window_size:]
                
                # Process accumulated audio frequently (every ~100ms of content)
                if len(accumulated_audio) > 4000:  # ~100ms of audio at 16kHz mono with 16-bit depth
                    # Process current audio chunk
                    current_time = time.time()
                    last_speech_time = current_time
                    
                    # Use recent buffer to process a larger context for better accuracy
                    process_audio = bytearray(buffer_window) + bytearray(accumulated_audio[-4000:])
                    
                    # Get transcription in background and continue receiving audio
                    asyncio.create_task(
                        process_and_update_transcript(process_audio, current_transcript, send_to_client)
                    )
                    
                    # Reset accumulated audio but keep some overlap for context
                    accumulated_audio = accumulated_audio[-500:]  # Keep last bit for context
                
            except asyncio.TimeoutError:
                # Check for silence to trigger processing
                current_time = time.time()
                if accumulated_audio and (last_speech_time is None or 
                        (current_time - last_speech_time) * 1000 >= silence_threshold):
                    
                    # Process silence-triggered transcription
                    if len(accumulated_audio) > 500:  # Only process if we have meaningful audio
                        # Process with buffer context
                        process_audio = bytearray(buffer_window) + bytearray(accumulated_audio)
                        
                        # Get transcription
                        transcript_text = await transcribe_chunk(process_audio)
                        
                        if transcript_text:
                            current_transcript = transcript_text
                            await send_to_client({
                                "type": "partial",
                                "text": transcript_text,
                                "is_final": False,
                                "status": "transcribing"
                            })
                    
                    # Reset for next utterance
                    accumulated_audio = bytearray()
                    last_speech_time = None
                
    except Exception as e:
        logger.error(f"Error in streaming transcription: {str(e)}")
        await send_to_client({
            "type": "error",
            "error": str(e),
            "is_final": True,
            "status": "error"
        })
    finally:
        # Clean up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def process_and_update_transcript(audio_data, current_text, send_to_client):
    """Process audio chunk and update the transcript."""
    try:
        # Get transcription
        transcript_text = await transcribe_chunk(audio_data)
        
        if transcript_text and transcript_text.strip():
            # Send update
            await send_to_client({
                "type": "partial",
                "text": transcript_text,
                "is_final": False,
                "status": "transcribing"
            })
            return transcript_text
        return current_text
    except Exception as e:
        logger.error(f"Error processing transcript update: {str(e)}")
        return current_text

async def transcribe_chunk(audio_data):
    """Transcribe a small audio chunk with minimal latency."""
    if not audio_data:
        return ""
        
    temp_file_path = None
    try:
        # Create temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Use whisper-1 for fastest response time
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",  # Fastest model for lowest latency
                language="en",
                response_format="text"
            )
        
        transcript_text = response.text if hasattr(response, 'text') else str(response)
        return transcript_text.strip()
    except Exception as e:
        logger.error(f"Error transcribing chunk: {str(e)}")
        return ""
    finally:
        # Clean up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def process_audio_stream(audio_queue, send_to_client) -> None:
    """
    Process audio chunks from the queue and send transcription results to the client
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
    """
    temp_file_path = None
    accumulated_audio = bytearray()
    
    try:
        # Collect audio chunks
        while True:
            chunk = await audio_queue.get()
            if chunk is None:  # None signals end of stream
                break
            
            # Accumulate audio data
            accumulated_audio.extend(chunk)
        
        # If we have audio data to process
        if accumulated_audio:
            # Create a temporary file for the complete audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(accumulated_audio)
            
            # Log file information
            logger.info(f"Created temporary file {temp_file_path} with {len(accumulated_audio)} bytes")
            
            # Transcribe the complete audio
            try:
                with open(temp_file_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",  # Changed to a more reliable model
                        language="en"
                    )
                
                transcript_text = response.text if hasattr(response, 'text') else str(response)
                
                if transcript_text and transcript_text.strip():
                    # Send transcription to client
                    await send_to_client({
                        "text": transcript_text.strip(),
                        "is_final": True
                    })
                    
                    logger.info(f"Transcription: {transcript_text[:100]}...")
                else:
                    await send_to_client({
                        "text": "No transcription available",
                        "is_final": True
                    })
                    logger.warning("No transcription was returned")
            except Exception as e:
                logger.error(f"Error during transcription: {str(e)}")
                await send_to_client({
                    "error": f"Transcription error: {str(e)}",
                    "is_final": True
                })
            finally:
                # Clean up the temp file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    temp_file_path = None
        else:
            await send_to_client({
                "error": "No audio data received",
                "is_final": True
            })
            
    except Exception as e:
        logger.error(f"Error in transcription processing: {str(e)}")
        await send_to_client({
            "error": str(e),
            "is_final": True
        })
    finally:
        # Make sure temp file is cleaned up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {str(e)}")

async def process_incremental_audio_stream(audio_queue, send_to_client, context="") -> None:
    """
    Process audio chunks incrementally from the queue, transcribing periodically and formatting with LLM.
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
        context: Optional context to help with formatting the transcription
    """
    temp_file_path = None
    accumulated_audio = bytearray()
    last_transcription_time = time.time()
    transcription_interval = 7  # seconds between transcriptions
    full_transcript = ""
    chunk_counter = 0
    
    try:
        # Send initial status to client
        await send_to_client({
            "text": "Listening...",
            "is_final": False,
            "status": "listening",
            "formatted": False
        })
        
        while True:
            try:
                # Wait for a chunk with timeout to allow periodic processing
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
                if chunk is None:  # None signals end of stream
                    # Process final accumulated audio
                    if accumulated_audio:
                        transcript_text = await transcribe_audio(accumulated_audio)
                        if transcript_text:
                            full_transcript = await format_transcript_with_llm(transcript_text, context, is_final=True)
                            await send_to_client({
                                "text": transcript_text,
                                "formatted_text": full_transcript,
                                "is_final": True,
                                "status": "completed",
                                "formatted": True
                            })
                    break
                
                # Accumulate audio data
                accumulated_audio.extend(chunk)
                chunk_counter += 1
                
                # Send status update every 10 chunks
                if chunk_counter % 10 == 0:
                    await send_to_client({
                        "text": "Recording...",
                        "is_final": False,
                        "status": "recording",
                        "bytes_received": len(accumulated_audio),
                        "formatted": False
                    })
                
            except asyncio.TimeoutError:
                # Check if it's time to process accumulated audio
                current_time = time.time()
                if current_time - last_transcription_time >= transcription_interval and accumulated_audio:
                    last_transcription_time = current_time
                    
                    # Create a copy of the accumulated audio for transcription
                    audio_to_process = bytearray(accumulated_audio)
                    
                    # Transcribe the current audio
                    await send_to_client({
                        "text": "Processing interim transcription...",
                        "is_final": False,
                        "status": "transcribing",
                        "formatted": False
                    })
                    
                    transcript_text = await transcribe_audio(audio_to_process)
                    if transcript_text:
                        # Format with LLM
                        formatted_text = await format_transcript_with_llm(transcript_text, context)
                        
                        # Send interim result
                        await send_to_client({
                            "text": transcript_text,
                            "formatted_text": formatted_text,
                            "is_final": False,
                            "status": "interim_result",
                            "timestamp": current_time,
                            "formatted": True
                        })
                        
                        logger.info(f"Interim transcription: {transcript_text[:100]}...")
    except Exception as e:
        logger.error(f"Error in incremental transcription: {str(e)}")
        await send_to_client({
            "error": str(e),
            "is_final": True,
            "status": "error",
            "formatted": False
        })

async def transcribe_audio(audio_data: bytearray) -> str:
    """Transcribe audio data using Whisper model."""
    temp_file_path = None
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Transcribe the audio
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",  # Using the most advanced Whisper model
                language="en",
                response_format="text"
            )
        
        transcript_text = response.text if hasattr(response, 'text') else str(response)
        return transcript_text.strip()
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return ""
    finally:
        # Clean up the temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {str(e)}")

async def format_transcript_with_llm(transcript: str, context: str = "", is_final: bool = False) -> str:
    """Format a transcript with an LLM using provided context."""
    try:
        # Prepare the prompt
        action_type = "final formatting" if is_final else "interim formatting"
        prompt = TRANSCRIPTION_FORMATTING_PROMPT.format(
            transcript=transcript,
            context=context,
            action_type=action_type
        )

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": TRANSCRIPTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        formatted_text = response.choices[0].message.content.strip()
        return formatted_text
    
    except Exception as e:
        logger.error(f"Error formatting transcript with LLM: {str(e)}")
        return transcript  # Return original if formatting fails

async def process_realtime_audio_stream(audio_queue, send_to_client) -> None:
    """
    Process audio in real-time with immediate transcription updates and later refinement.
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
    """
    accumulated_audio = bytearray()
    temp_file_path = None
    last_chunk_time = time.time()
    last_update_time = time.time()
    chunk_counter = 0
    transcript_buffer = ""
    
    # Smaller chunk duration for faster updates (2 seconds)
    realtime_chunk_duration = 2.0
    # How often to send updates at minimum (0.5 seconds)
    min_update_interval = 0.5
    
    try:
        # Send initial status to client
        await send_to_client({
            "text": "Listening...",
            "is_final": False,
            "status": "listening",
            "realtime": True
        })
        
        while True:
            try:
                # Short timeout for very responsive updates
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                
                # End of stream
                if chunk is None:
                    # Process final audio and send refined transcription
                    if accumulated_audio:
                        await send_to_client({
                            "text": "Finalizing transcription...",
                            "is_final": False,
                            "status": "finalizing",
                            "realtime": True
                        })
                        # Final transcription with better model
                        transcript_text = await transcribe_audio_for_final(accumulated_audio)
                        await send_to_client({
                            "text": transcript_text,
                            "is_final": True,
                            "status": "completed",
                            "realtime": True,
                            "refined": True
                        })
                    break
                
                # Add chunk to accumulated audio
                accumulated_audio.extend(chunk)
                chunk_counter += 1
                current_time = time.time()
                
                # Process in real-time after collecting enough audio (2s) or on regular intervals
                if (current_time - last_chunk_time >= realtime_chunk_duration or 
                        chunk_counter % 10 == 0) and current_time - last_update_time >= min_update_interval:
                    
                    # Create a copy of accumulated audio for processing
                    audio_to_process = bytearray(accumulated_audio)
                    
                    # Process in background to avoid blocking
                    asyncio.create_task(
                        process_audio_chunk_realtime(audio_to_process, send_to_client)
                    )
                    
                    last_chunk_time = current_time
                    last_update_time = current_time
                
            except asyncio.TimeoutError:
                # Check if we should process accumulated audio
                current_time = time.time()
                if accumulated_audio and current_time - last_update_time >= min_update_interval:
                    # Process and update transcript
                    audio_to_process = bytearray(accumulated_audio)
                    asyncio.create_task(
                        process_audio_chunk_realtime(audio_to_process, send_to_client)
                    )
                    last_update_time = current_time
    
    except Exception as e:
        logger.error(f"Error in real-time transcription: {str(e)}")
        await send_to_client({
            "error": str(e),
            "is_final": True,
            "status": "error",
            "realtime": True
        })

async def process_audio_chunk_realtime(audio_data, send_to_client):
    """Process audio chunk for real-time transcription using faster model."""
    temp_file_path = None
    try:
        # Create temporary file for the audio chunk
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Use faster model for real-time updates
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",  # Faster model for real-time
                language="en",
                response_format="text"
            )
        
        transcript_text = response.text if hasattr(response, 'text') else str(response)
        if transcript_text and transcript_text.strip():
            # Send immediate update
            await send_to_client({
                "text": transcript_text.strip(),
                "is_final": False,
                "status": "transcribing",
                "realtime": True,
                "refined": False
            })
    except Exception as e:
        logger.error(f"Error processing audio chunk: {str(e)}")
    finally:
        # Clean up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def transcribe_audio_for_final(audio_data: bytearray) -> str:
    """Transcribe audio for final result using the best model."""
    temp_file_path = None
    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Use best model for final transcription
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",  # Best model for final transcription
                language="en",
                response_format="text"
            )
        
        transcript_text = response.text if hasattr(response, 'text') else str(response)
        return transcript_text.strip()
    
    except Exception as e:
        logger.error(f"Error in final transcription: {str(e)}")
        return ""
    finally:
        # Clean up the temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {str(e)}")

async def process_live_streaming_audio(audio_queue, send_to_client) -> None:
    """
    Process audio in real-time with improved latency and reliability.
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
    """
    accumulated_audio = bytearray()
    last_update_time = time.time()
    update_interval = 0.3  # Reduced to 300ms for better responsiveness
    buffer_size_threshold = 4000  # Process when buffer reaches ~250ms of audio at 16kHz
    
    try:
        # Send initial status to client
        await send_to_client({
            "text": "Listening...",
            "is_final": False,
            "status": "listening",
            "live": True
        })
        
        # Create separate buffer for complete sentences to reduce fluctuations
        current_transcript = ""
        
        while True:
            # Get audio chunk with timeout
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1) # Shorter timeout for better responsiveness
                
                # End of stream
                if chunk is None:
                    # Final processing of accumulated audio
                    if accumulated_audio:
                        final_text = await simple_transcribe(accumulated_audio)
                        if final_text:
                            await send_to_client({
                                "text": final_text,
                                "is_final": True,
                                "status": "completed",
                                "live": True
                            })
                    break
                
                # Add chunk to accumulated audio
                accumulated_audio.extend(chunk)
                current_time = time.time()
                
                # Process audio if enough time has passed OR we have enough data
                if (current_time - last_update_time >= update_interval or 
                        len(accumulated_audio) >= buffer_size_threshold):
                    
                    # Process in a background task to not block receiving more audio
                    asyncio.create_task(
                        process_and_update_transcript(
                            bytearray(accumulated_audio),
                            send_to_client,
                            current_transcript
                        )
                    )
                    
                    # Reset timer
                    last_update_time = current_time
            
            except asyncio.TimeoutError:
                # Check if we should process any accumulated audio
                current_time = time.time()
                if accumulated_audio and current_time - last_update_time >= update_interval:
                    asyncio.create_task(
                        process_and_update_transcript(
                            bytearray(accumulated_audio),
                            send_to_client,
                            current_transcript
                        )
                    )
                    last_update_time = current_time
    
    except Exception as e:
        logger.error(f"Error in live streaming transcription: {str(e)}")
        await send_to_client({
            "error": str(e),
            "is_final": True,
            "status": "error",
            "live": True
        })

async def process_and_update_transcript(audio_data, send_to_client, current_transcript):
    """Process audio and send only meaningful updates to reduce flickering."""
    try:
        # Get new transcript
        new_transcript = await simple_transcribe(audio_data)
        
        if new_transcript and new_transcript.strip():
            # Only send if the transcript has meaningful content
            await send_to_client({
                "text": new_transcript,
                "is_final": False,
                "status": "transcribing",
                "live": True
            })
            
            return new_transcript
        
        return current_transcript
    
    except Exception as e:
        logger.error(f"Error processing transcript update: {str(e)}")
        return current_transcript

async def simple_transcribe(audio_data: bytearray) -> str:
    """Simple function to transcribe audio data using Whisper."""
    temp_file_path = None
    try:
        # Create temporary file for the audio data
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Use a faster model with response_format="text" for speed
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",  # Use the fastest model
                language="en",
                response_format="text"
            )
        
        return response.text.strip() if hasattr(response, 'text') else str(response).strip()
    
    except Exception as e:
        logger.error(f"Error in simple transcription: {str(e)}")
        return ""
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

# Add this new async function for enhanced live transcription with VAD support
async def enhanced_streaming_transcription(audio_queue, send_to_client) -> None:
    """
    Enhanced streaming transcription with Voice Activity Detection (VAD) and 
    progressive chunking for better real-time performance.
    
    Args:
        audio_queue: AsyncIO queue containing audio chunks
        send_to_client: Async function to send results to the client
    """
    # Initialize buffers and state
    audio_buffer = bytearray()  # Main audio buffer
    continuous_buffer = bytearray()  # Rolling buffer for context
    vad_buffer = bytearray()  # Buffer for VAD processing
    
    # Configuration parameters
    max_buffer_size = 40000  # About 2.5 seconds at 16kHz
    min_silence_ms = 400  # Minimum silence to consider a pause
    context_size = 16000  # Context size (1 second at 16kHz)
    immediate_interval = 50  # Process chunks every 50ms for instant feedback
    last_process_time = time.time()
    last_vad_check_time = time.time()
    
    # State tracking
    is_speaking = False
    last_transcript = ""
    cumulative_transcript = ""
    
    try:
        # Send initial status
        await send_to_client({
            "text": "Listening for speech...",
            "is_final": False,
            "status": "listening"
        })
        
        while True:
            try:
                # Wait for audio data with a short timeout for responsive processing
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.05)
                
                # End signal received
                if chunk is None:
                    # Process any remaining audio
                    if len(audio_buffer) > 0:
                        # Final pass with the best model
                        final_transcript = await transcribe_with_model(audio_buffer, "whisper-large-v3")
                        await send_to_client({
                            "text": final_transcript,
                            "is_final": True,
                            "status": "completed"
                        })
                    break
                
                # Add to buffers
                audio_buffer.extend(chunk)
                continuous_buffer.extend(chunk)
                vad_buffer.extend(chunk)
                
                # Trim continuous buffer to reasonable size for context
                if len(continuous_buffer) > max_buffer_size * 2:
                    continuous_buffer = continuous_buffer[-max_buffer_size:]
                
                # Check for voice activity periodically
                current_time = time.time()
                if len(vad_buffer) >= 4000 and current_time - last_vad_check_time > 0.1:  # 100ms VAD check
                    is_active = await detect_voice_activity(vad_buffer)
                    
                    # State transition: silence -> speech
                    if is_active and not is_speaking:
                        is_speaking = True
                        # Include some pre-buffer for context
                        audio_buffer = continuous_buffer[-context_size:] + audio_buffer
                        await send_to_client({
                            "text": "Speech detected...",
                            "is_final": False,
                            "status": "speech_detected"
                        })
                    
                    # State transition: speech -> silence
                    elif not is_active and is_speaking:
                        # If we've been speaking but now detecting silence, wait a bit before finalizing
                        # This prevents cutting off sentences during brief pauses
                        silence_duration = await measure_silence_duration(vad_buffer)
                        if silence_duration > min_silence_ms:
                            is_speaking = False
                            # Process the utterance if it's reasonably sized
                            if len(audio_buffer) > 1000:  # Only process if we have enough speech data
                                transcript = await transcribe_with_model(audio_buffer, "whisper-1")
                                if transcript and transcript.strip():
                                    # Smart handling of sentence fragments
                                    transcript = await smart_merge_transcript(transcript, last_transcript)
                                    cumulative_transcript += " " + transcript if cumulative_transcript else transcript
                                    last_transcript = transcript
                                    
                                    await send_to_client({
                                        "text": transcript,
                                        "cumulative_text": cumulative_transcript,
                                        "is_final": False,
                                        "status": "transcribed_segment",
                                        "contains_ending": transcript.strip().endswith((".","?","!"))
                                    })
                            # Reset the audio buffer but keep the continuous buffer
                            audio_buffer = bytearray()
                    
                    # Reset VAD buffer and timer
                    vad_buffer = bytearray()
                    last_vad_check_time = current_time
                
                # Periodic processing for immediate feedback during long speech segments
                if is_speaking and current_time - last_process_time >= immediate_interval/1000 and len(audio_buffer) > 2000:
                    last_process_time = current_time
                    
                    # Process a copy to avoid modifying the buffer
                    buffer_copy = bytearray(audio_buffer)
                    asyncio.create_task(process_and_send_immediate_feedback(
                        buffer_copy, send_to_client, last_transcript
                    ))
                
                # Safety check - if buffer gets too large, force process it
                if len(audio_buffer) > max_buffer_size:
                    transcript = await transcribe_with_model(audio_buffer, "whisper-1")
                    if transcript and transcript.strip():
                        # Update both transcripts
                        last_transcript = transcript
                        cumulative_transcript += " " + transcript if cumulative_transcript else transcript
                        
                        await send_to_client({
                            "text": transcript,
                            "cumulative_text": cumulative_transcript,
                            "is_final": False,
                            "status": "transcribed_long_segment"
                        })
                    # Keep a portion for context but reset the buffer
                    audio_buffer = audio_buffer[-4000:]
            
            except asyncio.TimeoutError:
                # Just continue - this allows us to check if we need to process
                # the current buffer even when no new audio is coming in
                pass
                
    except Exception as e:
        logger.error(f"Error in enhanced streaming transcription: {str(e)}")
        await send_to_client({
            "error": str(e),
            "is_final": True,
            "status": "error"
        })

async def detect_voice_activity(audio_data, threshold=0.005):
    """
    Detect if audio contains speech using simple energy-based VAD.
    
    Args:
        audio_data: Raw audio bytes
        threshold: Energy threshold for speech detection
        
    Returns:
        bool: True if speech is detected, False otherwise
    """
    try:
        # Convert byte array to samples
        # Assuming 16-bit PCM audio at 16kHz
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Normalize to [-1.0, 1.0]
        samples = samples / 32768.0
        
        # Calculate RMS energy
        energy = np.sqrt(np.mean(samples**2))
        
        # Detect speech based on energy threshold
        return energy > threshold
    except Exception as e:
        logger.error(f"Error in VAD: {str(e)}")
        return False  # Default to no speech on error

async def measure_silence_duration(audio_data):
    """
    Measure the duration of silence at the end of the audio buffer.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        float: Duration of trailing silence in milliseconds
    """
    try:
        # Convert bytes to audio segment using pydub
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Load as audio segment
        audio = AudioSegment.from_file(temp_file_path, format="wav")
        
        # Detect non-silent chunks
        non_silent_ranges = detect_nonsilent(
            audio, 
            min_silence_len=50,  # Minimum silence length in ms
            silence_thresh=-35    # Silence threshold in dBFS
        )
        
        # If we have non-silent ranges, calculate silence at the end
        if non_silent_ranges:
            last_non_silent_end = non_silent_ranges[-1][1]
            silence_duration = len(audio) - last_non_silent_end
            return silence_duration
        
        return len(audio)  # All silence
    
    except Exception as e:
        logger.error(f"Error measuring silence: {str(e)}")
        return 0  # Default to no silence on error
    finally:
        # Clean up temp file
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def smart_merge_transcript(new_transcript, previous_transcript):
    """
    Intelligently merge transcripts to avoid repetition and 
    ensure proper sentence continuity.
    
    Args:
        new_transcript: Latest transcript segment
        previous_transcript: Previous transcript segment
        
    Returns:
        str: Merged transcript
    """
    if not previous_transcript:
        return new_transcript
    
    # Check for overlap or if the new transcript is a more complete version of the old one
    if len(new_transcript) >= len(previous_transcript):
        # If new transcript includes all or most of the previous one
        if previous_transcript.lower() in new_transcript.lower():
            return new_transcript
        
        # Check for partial sentence completion
        words_previous = previous_transcript.split()
        words_new = new_transcript.split()
        
        # Try to find overlap
        overlap_size = min(4, min(len(words_previous), len(words_new)))
        for i in range(overlap_size, 0, -1):
            if words_previous[-i:] == words_new[:i]:
                # Found overlap, merge
                return previous_transcript + ' ' + ' '.join(words_new[i:])
    
    # Default to just appending with space if we can't find a better merge
    return new_transcript

async def process_and_send_immediate_feedback(audio_data, send_to_client, previous_transcript):
    """
    Process a chunk of audio for immediate feedback during long speech segments.
    
    Args:
        audio_data: Audio data buffer
        send_to_client: Function to send updates to client
        previous_transcript: Previous transcript for context
    """
    try:
        # Use the fastest model for immediate feedback
        transcript = await transcribe_with_model(audio_data, "whisper-1")
        if transcript and transcript.strip():
            # For immediate feedback, we don't need to be as careful with merging
            await send_to_client({
                "text": transcript,
                "is_final": False,
                "status": "immediate_feedback"
            })
    except Exception as e:
        logger.error(f"Error in immediate feedback: {str(e)}")

async def transcribe_with_model(audio_data, model_name="whisper-1"):
    """
    Transcribe audio using the specified Whisper model.
    
    Args:
        audio_data: Raw audio bytes
        model_name: Whisper model to use
        
    Returns:
        str: Transcript text
    """
    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_data)
        
        # Transcribe with specified model
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model=model_name,
                language="en",
                response_format="text"
            )
        
        transcript_text = response.text if hasattr(response, 'text') else str(response)
        return transcript_text.strip()
    
    except Exception as e:
        logger.error(f"Error transcribing with model {model_name}: {str(e)}")
        return ""
    finally:
        # Clean up
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

# Optimized real-time transcription with enhanced VAD and smooth streaming
async def optimized_live_transcription(audio_queue, send_to_client) -> None:
    """
    Optimized live transcription with enhanced Voice Activity Detection and smooth streaming.
    Provides immediate feedback with progressive refinement.
    """
    # Buffers for different processing stages
    immediate_buffer = bytearray()  # For instant feedback (50-100ms)
    speech_buffer = bytearray()     # For speech segments
    context_buffer = bytearray()    # For context and accuracy
    
    # State tracking
    is_speaking = False
    speech_start_time = None
    last_activity_time = time.time()
    last_immediate_time = time.time()
    last_speech_time = time.time()
    
    # Configuration
    immediate_threshold = 2000      # ~125ms at 16kHz
    speech_threshold = 8000         # ~500ms at 16kHz  
    silence_timeout = 1.0           # 1 second silence
    immediate_interval = 0.05       # 50ms for immediate feedback
    speech_interval = 0.3           # 300ms for speech segments
    max_context_size = 32000        # 2 seconds context
    
    # Transcription state
    last_immediate_text = ""
    last_speech_text = ""
    cumulative_text = ""
    
    try:
        # Send initial status
        await send_to_client({
            "text": "🎤 Ready to listen...",
            "type": "status",
            "is_final": False,
            "status": "ready",
            "timestamp": time.time()
        })
        
        while True:
            try:
                # Get audio chunk with short timeout for responsiveness
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.02)
                
                if chunk is None:
                    # End of stream - process any remaining audio
                    if speech_buffer:
                        final_text = await transcribe_with_optimized_model(speech_buffer, "final")
                        if final_text and final_text.strip():
                            cumulative_text += " " + final_text if cumulative_text else final_text
                            await send_to_client({
                                "text": final_text,
                                "cumulative_text": cumulative_text,
                                "type": "final",
                                "is_final": True,
                                "status": "completed",
                                "timestamp": time.time()
                            })
                    break
                
                # Add to all buffers
                immediate_buffer.extend(chunk)
                speech_buffer.extend(chunk)
                context_buffer.extend(chunk)
                
                # Maintain context buffer size
                if len(context_buffer) > max_context_size:
                    context_buffer = context_buffer[-max_context_size:]
                
                current_time = time.time()
                
                # Voice Activity Detection
                vad_result = await advanced_voice_activity_detection(chunk)
                
                if vad_result['is_speech']:
                    if not is_speaking:
                        # Speech started
                        is_speaking = True
                        speech_start_time = current_time
                        await send_to_client({
                            "text": "🎙️ Speech detected...",
                            "type": "speech_start",
                            "is_final": False,
                            "status": "speech_detected",
                            "timestamp": current_time
                        })
                    
                    last_activity_time = current_time
                    
                    # Immediate feedback processing
                    if (len(immediate_buffer) >= immediate_threshold and 
                        current_time - last_immediate_time >= immediate_interval):
                        
                        asyncio.create_task(
                            process_immediate_feedback(
                                bytearray(immediate_buffer[-immediate_threshold:]),
                                send_to_client,
                                last_immediate_text
                            )
                        )
                        last_immediate_time = current_time
                    
                    # Speech segment processing
                    if (len(speech_buffer) >= speech_threshold and 
                        current_time - last_speech_time >= speech_interval):
                        
                        asyncio.create_task(
                            process_speech_segment(
                                bytearray(speech_buffer),
                                send_to_client,
                                context_buffer,
                                cumulative_text
                            )
                        )
                        last_speech_time = current_time
                        
                        # Keep some overlap for continuity
                        speech_buffer = speech_buffer[-speech_threshold//2:]
                        
                else:
                    # Silence detected
                    if is_speaking and current_time - last_activity_time >= silence_timeout:
                        # End of speech segment
                        is_speaking = False
                        
                        if speech_buffer:
                            # Process final speech segment
                            final_segment = await transcribe_with_optimized_model(speech_buffer, "segment")
                            if final_segment and final_segment.strip():
                                # Smart merging with previous text
                                merged_text = await smart_text_merger(cumulative_text, final_segment)
                                cumulative_text = merged_text
                                
                                await send_to_client({
                                    "text": final_segment,
                                    "cumulative_text": cumulative_text,
                                    "type": "speech_end",
                                    "is_final": False,
                                    "status": "speech_completed",
                                    "timestamp": current_time,
                                    "confidence": vad_result.get('confidence', 0.8)
                                })
                            
                            # Clear speech buffer
                            speech_buffer = bytearray()
                        
                        await send_to_client({
                            "text": "🔇 Silence detected",
                            "type": "silence",
                            "is_final": False,
                            "status": "silence_detected",
                            "timestamp": current_time
                        })
                
                # Clear immediate buffer periodically
                if len(immediate_buffer) > immediate_threshold * 2:
                    immediate_buffer = immediate_buffer[-immediate_threshold:]
                    
            except asyncio.TimeoutError:
                # No new audio - check for silence timeout
                current_time = time.time()
                if is_speaking and current_time - last_activity_time >= silence_timeout:
                    is_speaking = False
                    if speech_buffer:
                        # Process remaining speech
                        remaining_text = await transcribe_with_optimized_model(speech_buffer, "segment")
                        if remaining_text and remaining_text.strip():
                            cumulative_text += " " + remaining_text if cumulative_text else remaining_text
                            await send_to_client({
                                "text": remaining_text,
                                "cumulative_text": cumulative_text,
                                "type": "timeout_speech",
                                "is_final": False,
                                "status": "timeout_processed",
                                "timestamp": current_time
                            })
                        speech_buffer = bytearray()
                continue
                
    except Exception as e:
        logger.error(f"Error in optimized live transcription: {str(e)}")
        await send_to_client({
            "error": f"Transcription error: {str(e)}",
            "type": "error",
            "is_final": True,
            "status": "error",
            "timestamp": time.time()
        })

async def process_immediate_feedback(audio_data, send_to_client, previous_text):
    """Process immediate feedback for ultra-responsive transcription."""
    try:
        # Use fastest model for immediate response
        text = await transcribe_with_optimized_model(audio_data, "immediate")
        if text and text.strip() and text.strip() != previous_text:
            await send_to_client({
                "text": text.strip(),
                "type": "immediate",
                "is_final": False,
                "status": "immediate_feedback",
                "confidence": 0.6,  # Lower confidence for immediate
                "timestamp": time.time()
            })
    except Exception as e:
        logger.error(f"Error in immediate feedback: {str(e)}")

async def process_speech_segment(audio_data, send_to_client, context_buffer, cumulative_text):
    """Process speech segments with context for better accuracy."""
    try:
        # Use medium accuracy model with context
        text = await transcribe_with_optimized_model(audio_data, "segment", context_buffer[-8000:])
        if text and text.strip():
            # Smart merging with cumulative text
            merged_text = await smart_text_merger(cumulative_text, text)
            
            await send_to_client({
                "text": text.strip(),
                "cumulative_text": merged_text,
                "type": "segment",
                "is_final": False,
                "status": "segment_processed",
                "confidence": 0.8,
                "timestamp": time.time()
            })
    except Exception as e:
        logger.error(f"Error in speech segment processing: {str(e)}")

async def advanced_voice_activity_detection(audio_chunk):
    """Advanced Voice Activity Detection with confidence scoring."""
    try:
        # Convert audio to numpy array for analysis
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_array.astype(float) ** 2))
        
        # Calculate zero crossing rate
        zero_crossings = np.sum(np.diff(np.sign(audio_array)) != 0)
        zcr = zero_crossings / len(audio_array)
        
        # Calculate spectral features (simplified)
        fft = np.fft.fft(audio_array)
        spectral_energy = np.sum(np.abs(fft[:len(fft)//2]))
        
        # Simple thresholding (can be improved with ML model)
        energy_threshold = 500
        zcr_threshold = 0.1
        spectral_threshold = 100000
        
        is_speech = (rms > energy_threshold and 
                    zcr > zcr_threshold and 
                    spectral_energy > spectral_threshold)
        
        # Calculate confidence based on how far above thresholds
        confidence = min(1.0, (rms / energy_threshold + 
                              zcr / zcr_threshold + 
                              spectral_energy / spectral_threshold) / 3)
        
        return {
            'is_speech': is_speech,
            'confidence': confidence,
            'rms': rms,
            'zcr': zcr,
            'spectral_energy': spectral_energy
        }
        
    except Exception as e:
        logger.error(f"Error in VAD: {str(e)}")
        return {'is_speech': True, 'confidence': 0.5}  # Default to speech

async def transcribe_with_optimized_model(audio_data, mode="segment", context_audio=None):
    """Transcribe with different models based on mode for optimal speed/accuracy trade-off."""
    if not audio_data or len(audio_data) < 100:
        return ""
    
    temp_file_path = None
    try:
        # Create temp file with context if provided
        audio_to_process = audio_data
        if context_audio and mode in ["segment", "final"]:
            # Add context for better accuracy
            audio_to_process = context_audio + audio_data
        
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(audio_to_process)
        
        # Choose model based on mode
        model_config = {
            "immediate": {"model": "whisper-1", "temperature": 0.2},
            "segment": {"model": "whisper-1", "temperature": 0.1},
            "final": {"model": "whisper-large-v3", "temperature": 0.0}
        }
        
        config = model_config.get(mode, model_config["segment"])
        
        with open(temp_file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model=config["model"],
                language="en",
                response_format="text",
                temperature=config["temperature"]
            )
        
        text = response.text if hasattr(response, 'text') else str(response)
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error in optimized transcription ({mode}): {str(e)}")
        return ""
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def smart_text_merger(existing_text, new_text):
    """Intelligently merge new text with existing text to avoid duplicates."""
    if not existing_text:
        return new_text
    
    if not new_text:
        return existing_text
    
    # Simple overlap detection and merging
    existing_words = existing_text.split()
    new_words = new_text.split()
    
    # Find overlap
    max_overlap = min(len(existing_words), len(new_words), 5)  # Check last 5 words
    
    for i in range(max_overlap, 0, -1):
        if existing_words[-i:] == new_words[:i]:
            # Found overlap, merge
            merged = existing_words + new_words[i:]
            return ' '.join(merged)
    
    # No overlap found, just append
    return existing_text + ' ' + new_text