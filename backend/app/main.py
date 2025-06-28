from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
import base64
import time
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
import os

from app.models import (
    TranscriptionContext,
    VexaMeetingRequest,
    VexaMeetingResponse,
    VexaTranscriptResponse,
    ConversationAnalysisRequest,
    ConversationAnalysisResponse
)
from app.config import (
    VEXA_API_KEY,
    VEXA_BASE_URL,
    MAX_RESPONSE_LENGTH,
    DEFAULT_TONE
)

from app.utils.transcription import (
    process_audio_stream, 
    process_incremental_audio_stream, 
    process_realtime_audio_stream,
    process_live_streaming_audio,
    process_streaming_audio,  # Import our new optimized function
    enhanced_streaming_transcription,  # Import for the enhanced streaming transcription function
    optimized_live_transcription  # Import our new optimized live transcription
)
from app.utils.vexa_client import (
    request_meeting_bot,
    get_meeting_transcript,
    get_bot_status,
    update_bot_config,
    stop_meeting_bot,
    list_meetings,
    update_meeting_data,
    delete_meeting,
    set_webhook_url,
    join_meeting,
    get_meeting_transcripts,
    leave_meeting
)
# Import conversation analysis function
from app.utils.openai_client import analyze_conversation
from app.utils.enhanced_rag import enhanced_rag_analyze
from app.utils.vector_db_manager import vector_db_manager
from app.utils.answer_cache import AnswerCache
from app.data.canonical_questions import get_canonical_questions_list
import hashlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Sales Assistant API Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import file management router
from app.api.file_management import router as file_router

# Add file management routes
app.include_router(file_router)

# Initialize answer cache
answer_cache = AnswerCache()

# Dictionary to store active websocket connections
active_connections = {}

@app.get("/")
async def root():
    return {"message": "Sales Assistant API Backend is running"}



@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription using OpenAI's gpt-4o-transcribe.
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    # Create a queue for audio chunks
    audio_queue = asyncio.Queue()
    
    # Function to send messages back to the client
    async def send_to_client(data):
        await websocket.send_json(data)
    
    # Start the transcription process in a background task
    transcription_task = asyncio.create_task(
        process_audio_stream(audio_queue, send_to_client)
    )
    
    try:
        while True:
            # Receive audio data from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    await audio_queue.put(None)
                    await transcription_task
                    break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error processing websocket message: {str(e)}")
                await websocket.send_json({"error": str(e)})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up resources
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass

@app.websocket("/ws/transcribe-incremental")
async def websocket_transcribe_incremental(websocket: WebSocket):
    """
    WebSocket endpoint for real-time incremental transcription with LLM formatting.
    Sends transcription updates every 5-10 seconds and formats using context.
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    # Create a queue for audio chunks
    audio_queue = asyncio.Queue()
    context = ""
    
    # Function to send messages back to the client
    async def send_to_client(data):
        await websocket.send_json(data)
    
    # Start the incremental transcription process in a background task
    transcription_task = None
    
    try:
        # Wait for initial context message before starting transcription
        init_data = await websocket.receive_text()
        try:
            init_message = json.loads(init_data)
            
            if init_message.get("type") == "context":
                # Extract context information
                ctx_data = init_message.get("data", {})
                context_obj = TranscriptionContext(**ctx_data)
                
                # Format context string from object
                context_parts = []
                if context_obj.meeting_title:
                    context_parts.append(f"Meeting Title: {context_obj.meeting_title}")
                if context_obj.participants:
                    context_parts.append(f"Participants: {', '.join(context_obj.participants)}")
                if context_obj.topics:
                    context_parts.append(f"Topics: {', '.join(context_obj.topics)}")
                if context_obj.context:
                    context_parts.append(f"Additional Context: {context_obj.context}")
                
                context = "\n".join(context_parts)
                logger.info(f"Received context for transcription: {context[:100]}...")
                
                # Send acknowledgment
                await send_to_client({
                    "type": "context_received",
                    "status": "ready"
                })
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received for context")
        except Exception as e:
            logger.error(f"Error processing context: {str(e)}")
            await send_to_client({"error": str(e)})
        
        # Start the transcription task with context
        transcription_task = asyncio.create_task(
            process_incremental_audio_stream(audio_queue, send_to_client, context)
        )
        
        while True:
            # Receive audio data from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    await audio_queue.put(None)
                    await transcription_task
                    break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error processing websocket message: {str(e)}")
                await websocket.send_json({"error": str(e)})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up resources
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if transcription_task and not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass

@app.websocket("/ws/transcribe-realtime")
async def websocket_transcribe_realtime(websocket: WebSocket):
    """
    WebSocket endpoint for immediate real-time transcription with frequent updates.
    Provides lower-latency updates for live display and refines at the end.
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    # Create a queue for audio chunks
    audio_queue = asyncio.Queue()
    
    # Function to send messages back to the client
    async def send_to_client(data):
        await websocket.send_json(data)
    
    # Start the real-time transcription process in a background task
    transcription_task = asyncio.create_task(
        process_realtime_audio_stream(audio_queue, send_to_client)
    )
    
    try:
        while True:
            # Receive audio data from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    await audio_queue.put(None)
                    await transcription_task
                    break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error processing websocket message: {str(e)}")
                await websocket.send_json({"error": str(e)})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up resources
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass

@app.websocket("/ws/live-transcribe")
async def websocket_live_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for true real-time transcription with immediate streaming updates.
    Provides ultra-low-latency word-by-word updates with continuous streaming like Google captions.
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    # Create a queue for audio chunks
    audio_queue = asyncio.Queue()
    
    # Function to send messages back to the client
    async def send_to_client(data):
        await websocket.send_json(data)
    
    # Start the live streaming transcription process in a background task using our optimized function
    transcription_task = asyncio.create_task(
        process_streaming_audio(audio_queue, send_to_client)  # Use our new optimized function
    )
    
    try:
        while True:
            # Receive audio data from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    await audio_queue.put(None)
                    await transcription_task
                    break
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Error processing websocket message: {str(e)}")
                await websocket.send_json({"error": str(e)})
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up resources
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass

# Add this new WebSocket endpoint for enhanced live transcription
@app.websocket("/ws/enhanced-transcribe")
async def enhanced_transcribe_endpoint(websocket: WebSocket):
    """
    Enhanced WebSocket endpoint for live transcription with optimized VAD and smooth streaming.
    Provides immediate feedback with progressive refinement for the smoothest transcription experience.
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    # Create an audio data queue
    audio_queue = asyncio.Queue()
    
    # Define a function to send results back to the client
    async def send_results(data):
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending to client: {str(e)}")
    
    # Start a background task for processing the audio stream with our optimized function
    processing_task = asyncio.create_task(
        optimized_live_transcription(audio_queue, send_results)
    )
    
    try:
        # Keep receiving audio data from the client
        while True:
            try:
                # Receive binary audio data directly
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "bytes" in message:
                        # Binary audio data
                        audio_data = message["bytes"]
                        if len(audio_data) > 0:
                            await audio_queue.put(audio_data)
                        else:
                            # Empty bytes signal end of stream
                            await audio_queue.put(None)
                            break
                    elif "text" in message:
                        # JSON control messages
                        try:
                            control_msg = json.loads(message["text"])
                            if control_msg.get("type") == "end":
                                await audio_queue.put(None)
                                break
                            elif control_msg.get("type") == "config":
                                # Handle configuration updates
                                logger.info(f"Config update: {control_msg}")
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON control message")
                            
            except Exception as e:
                logger.error(f"Error receiving message: {str(e)}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"Enhanced transcription client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Enhanced transcription WebSocket error: {str(e)}")
    finally:
        # Clean up resources
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel processing task if still running
        if not processing_task.done():
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Enhanced transcription cleanup completed for {connection_id}")

# Define question request model
class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str
    confidence: Optional[float] = None

# Add endpoint for question answering
@app.post("/api/ai/answer", response_model=AnswerResponse)
async def get_ai_answer(request: QuestionRequest):
    """
    Get AI-generated answer for a question from real-time transcription.
    """
    try:
        question = request.question.strip()
        
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        # Here you can integrate with your preferred AI service
        # For example: OpenAI, Anthropic, or a local model
        
        # For now, using a simple rule-based approach for demonstration
        answer = generate_simple_answer(question)
        
        return AnswerResponse(answer=answer, confidence=0.85)
    
    except Exception as e:
        logging.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_simple_answer(question: str) -> str:
    """
    Generate a simple answer based on the question pattern.
    In production, replace this with an actual AI model call.
    """
    question_lower = question.lower()
    
    # Simple rule-based answers
    if any(keyword in question_lower for keyword in ["price", "cost", "how much"]):
        return "Our product is available in several tiers, starting at $99/month for the basic package and $299/month for the enterprise solution."
    
    elif any(keyword in question_lower for keyword in ["feature", "capabilities", "what can"]):
        return "Our product features AI-powered sales assistance, real-time transcription, question detection, sentiment analysis, and automated action item tracking."
    
    elif any(keyword in question_lower for keyword in ["support", "help", "contact"]):
        return "Our support team is available 24/7 via email at support@salesassist.ai or by phone at 1-800-555-1234."
    
    elif any(keyword in question_lower for keyword in ["trial", "free", "demo"]):
        return "Yes, we offer a 14-day free trial with full access to all features. No credit card required to sign up."
    
    elif any(keyword in question_lower for keyword in ["integration", "connect", "api"]):
        return "Our platform integrates with all major CRM systems including Salesforce, HubSpot, and Zoho. We also offer a comprehensive API for custom integrations."
    
    # Default response for other questions
    return "I don't have a specific answer for that question yet. For more information, please contact our sales team at sales@salesassist.ai."

# Import Vexa client
from app.utils.vexa_client import join_meeting, get_meeting_transcripts, leave_meeting

@app.post("/api/vexa/join", response_model=VexaMeetingResponse)
async def add_vexa_bot_to_meeting(request: VexaMeetingRequest):
    """
    Add Vexa bot to a meeting.
    
    Args:
        request: Meeting details including platform and native meeting ID
        
    Returns:
        Meeting details and status
    """
    try:
        result = await join_meeting(request.native_meeting_id, request.platform)
        
        if not result["success"]:
            logger.error(f"Failed to add Vexa bot: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        # Check if this is a connection error (DNS resolution failure, etc.)
        if result.get("is_connection_error"):
            raise HTTPException(
                status_code=503, 
                detail="Could not connect to Vexa API. Please check your network connection or try again later."
            )
        
        return result
    except Exception as e:
        logger.error(f"Error adding Vexa bot to meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vexa/transcripts/{platform}/{meeting_id}", response_model=VexaTranscriptResponse)
async def get_vexa_meeting_transcripts(platform: str, meeting_id: str):
    """
    Get transcripts from a Vexa meeting.
    
    Args:
        platform: The meeting platform (google_meet, zoom, teams)
        meeting_id: The meeting ID
        
    Returns:
        List of transcripts from the meeting
    """
    try:
        result = await get_meeting_transcripts(platform, meeting_id)
        
        if not result["success"]:
            logger.error(f"Failed to fetch Vexa transcripts: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        return result
    except Exception as e:
        logger.error(f"Error fetching Vexa meeting transcripts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vexa/leave/{platform}/{meeting_id}", response_model=VexaMeetingResponse)
async def remove_vexa_bot_from_meeting(platform: str, meeting_id: str):
    """
    Remove Vexa bot from a meeting.
    
    Args:
        platform: The platform name (google_meet, zoom, teams)
        meeting_id: The meeting ID
        
    Returns:
        Status of the leave operation
    """
    try:
        result = await leave_meeting(platform, meeting_id)
        
        if not result["success"]:
            logger.error(f"Failed to leave Vexa meeting: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        return result
    except Exception as e:
        logger.error(f"Error leaving Vexa meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add a health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.config import OPENAI_API_KEY
    
    # Get vector database status from the new manager
    stats = vector_db_manager.get_database_stats()
    
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "services": {
            "openai": bool(OPENAI_API_KEY),
            "vector_db": {
                "total_files": stats.get("total_files", 0),
                "total_chunks": stats.get("total_chunks", 0),
                "last_updated": stats.get("last_updated")
            }
        }
    }

# Add a cache statistics endpoint
# Initialize vector database at startup
@app.on_event("startup")
async def startup_event():
    """Initialize the application when it starts"""
    try:
        logger.info("Application startup complete")
        # Vector database is initialized automatically by the VectorDBManager
        stats = vector_db_manager.get_database_stats()
        logger.info(f"Vector database ready with {stats.get('total_chunks', 0)} chunks")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")

# Enhanced endpoint for analyzing conversation snippets using RAG
@app.post("/analyze", response_model=ConversationAnalysisResponse)
async def analyze_conversation_endpoint(request: ConversationAnalysisRequest):
    """
    Analyze a conversation snippet and provide AI-generated insights and response.
    Uses cache for zero-latency responses when available, otherwise uses RAG pipeline.
    """
    try:
        # Validate input
        if not request.conversation or len(request.conversation.strip()) < 3:
            raise HTTPException(status_code=400, detail="Conversation text is too short or empty")
            
        # Get response length and tone from request or use defaults
        max_length = request.max_response_length or MAX_RESPONSE_LENGTH
        tone = request.tone or DEFAULT_TONE
        
        # STEP 1: Check cache first for zero-latency response
        logger.info(f"Checking cache for query: '{request.conversation[:100]}...'")
        cached_result = answer_cache.get_cached_answer(request.conversation, threshold=0.7)
        
        if cached_result:
            logger.info("Cache hit! Returning cached response")
            # Update metadata to show this was from cache
            cached_result["meta"]["cache_hit"] = True
            cached_result["meta"]["processing_source"] = "cache"
            
            # Return cached response immediately (no need to store again)
            return ConversationAnalysisResponse(
                # Basic fields
                intent=cached_result.get("intent", "Unknown"),
                question=cached_result.get("question"),
                information_gap=cached_result.get("information_gap"),
                response=cached_result.get("response", ""),
                sentiment=cached_result.get("sentiment", "neutral"),
                
                # Enhanced fields
                straightforward_answer=cached_result.get("straightforward_answer", ""),
                star_response=cached_result.get("star_response"),
                comparison_table=cached_result.get("comparison_table"),
                relevant_bullets=cached_result.get("relevant_bullets", []),
                statistics=cached_result.get("statistics", {}),
                terminology_explainer=cached_result.get("terminology_explainer"),
                analogies_or_metaphors=cached_result.get("analogies_or_metaphors"),
                customer_story_snippet=cached_result.get("customer_story_snippet"),
                pricing_insight=cached_result.get("pricing_insight"),
                escalation_flag=cached_result.get("escalation_flag", False),
                follow_up_questions=cached_result.get("follow_up_questions", []),
                longform_response=cached_result.get("longform_response"),
                salesPoints=cached_result.get("salesPoints", []),
                meta=cached_result.get("meta", {})
            )
        
        # STEP 2: No cache hit, use enhanced RAG pipeline
        logger.info("No cache hit, using enhanced RAG pipeline")
        result = await enhanced_rag_analyze(
            conversation=request.conversation,
            max_response_length=max_length,
            tone=tone,
            include_sources=request.include_sources
        )
        
        # STEP 3: Store result in cache for future use
        if result and result.get("meta", {}).get("confidence", 0) > 0.7:
            logger.info("Storing high-confidence result in cache")
            result["meta"]["cache_hit"] = False
            result["meta"]["processing_source"] = "enhanced_rag"
            answer_cache.store_answer(request.conversation, result)
        
        # Convert the result to our response model
        logger.info(f"Raw result from enhanced_rag_analyze: {result}")
        
        try:
            return ConversationAnalysisResponse(
                # Basic fields
                intent=result.get("intent", "Unknown"),
                question=result.get("question"),
                information_gap=result.get("information_gap"),
                response=result.get("response", ""),
                sentiment=result.get("sentiment", "neutral"),
                
                # New enhanced fields
                straightforward_answer=result.get("straightforward_answer", ""),
                star_response=result.get("star_response"),
                comparison_table=result.get("comparison_table"),
                relevant_bullets=result.get("relevant_bullets", []),
                statistics=result.get("statistics", {}),
                terminology_explainer=result.get("terminology_explainer"),
                analogies_or_metaphors=result.get("analogies_or_metaphors"),
                customer_story_snippet=result.get("customer_story_snippet"),
                pricing_insight=result.get("pricing_insight"),
                escalation_flag=result.get("escalation_flag", False),
                follow_up_questions=result.get("follow_up_questions", []),
                longform_response=result.get("longform_response"),
                salesPoints=result.get("salesPoints", []),
                meta=result.get("meta", {})
            )
        except Exception as validation_error:
            logger.error(f"Pydantic validation error: {str(validation_error)}")
            logger.error(f"Problematic data - comparison_table: {result.get('comparison_table')}")
            raise
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== COMPLETE VEXA API ENDPOINTS =====
# These endpoints provide full Vexa integration as expected by the frontend

@app.post("/vexa/bots")
async def request_vexa_bot(request: VexaMeetingRequest):
    """
    Request a Vexa bot for a meeting (matches frontend vexaClient.requestBot).
    
    Args:
        request: Meeting details including platform, native_meeting_id, language, bot_name
        
    Returns:
        Meeting details and bot status
    """
    try:
        result = await request_meeting_bot(
            native_meeting_id=request.native_meeting_id,
            platform=request.platform,
            language=getattr(request, 'language', 'en'),
            bot_name=getattr(request, 'bot_name', 'Spiked AI Bot')
        )
        
        if not result["success"]:
            logger.error(f"Failed to request Vexa bot: {result.get('error')}")
            status_code = result.get('status_code', 500)
            error_message = result.get("error", "Unknown error")
            
            # Enhance error messages for common issues
            if status_code == 409:
                if "concurrent" in error_message.lower():
                    error_message = "You have reached your concurrent bot limit (1 bot). Please stop your existing bot first."
                elif "already exists" in error_message.lower() or "duplicate" in error_message.lower():
                    error_message = f"A bot is already running for this meeting. Please stop it first or use a different meeting URL."
                else:
                    error_message = f"Conflict: {error_message}"
            
            raise HTTPException(status_code=status_code, detail=error_message)
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting Vexa bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vexa/transcripts/{platform}/{meeting_id}")
async def get_vexa_transcript(platform: str, meeting_id: str):
    """
    Get real-time meeting transcript (matches frontend vexaClient.getTranscript).
    
    Args:
        platform: The meeting platform (google_meet, zoom, teams)
        meeting_id: The native meeting ID
        
    Returns:
        Real-time transcript data
    """
    try:
        result = await get_meeting_transcript(meeting_id, platform)
        
        if not result["success"]:
            # For transcript endpoints, we might get 404 if no transcript yet
            status_code = result.get('status_code', 500)
            if status_code == 404:
                # Return empty transcript data for frontend compatibility
                return {
                    "bot": {
                        "id": meeting_id,
                        "platform": platform,
                        "status": "active"
                    },
                    "segments": []
                }
            else:
                logger.error(f"Failed to get Vexa transcript: {result.get('error')}")
                raise HTTPException(
                    status_code=status_code, 
                    detail=result.get("error", "Unknown error")
                )
        
        # Format response for frontend compatibility
        data = result["data"]
        
        # Ensure we have the expected structure
        if "transcripts" in data:
            # Convert transcripts to segments format expected by frontend
            segments = []
            if isinstance(data["transcripts"], list):
                for transcript in data["transcripts"]:
                    segments.append({
                        "speaker": transcript.get("speaker", "Unknown"),
                        "text": transcript.get("text", ""),
                        "timestamp": transcript.get("timestamp", ""),
                        "confidence": transcript.get("confidence", 1.0)
                    })
        else:
            segments = data.get("segments", [])
        
        return {
            "bot": data.get("bot", {
                "id": meeting_id,
                "platform": platform,
                "status": "active"
            }),
            "segments": segments
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Vexa transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vexa/bots/status")
async def get_vexa_bot_status():
    """
    Get status of running bots (matches frontend vexaClient.getBotStatus).
    
    Returns:
        Status of all running bots
    """
    try:
        result = await get_bot_status()
        
        if not result["success"]:
            logger.error(f"Failed to get bot status: {result.get('error')}")
            # For bot status, we can return empty if there's an error
            return {"running_bots": []}
        
        # Ensure we return the data in the expected format
        data = result["data"]
        if isinstance(data, dict) and "running_bots" in data:
            return data
        else:
            # If the format is different, wrap it
            return {"running_bots": data if isinstance(data, list) else []}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/vexa/bots/{platform}/{meeting_id}/config")
async def update_vexa_bot_config(platform: str, meeting_id: str, config: dict):
    """
    Update bot configuration (matches frontend vexaClient.updateBotConfig).
    
    Args:
        platform: The meeting platform
        meeting_id: The native meeting ID
        config: Configuration to update
        
    Returns:
        Updated configuration response
    """
    try:
        result = await update_bot_config(meeting_id, platform, config)
        
        if not result["success"]:
            logger.error(f"Failed to update bot config: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vexa/bots/{platform}/{meeting_id}")
async def stop_vexa_bot(platform: str, meeting_id: str):
    """
    Stop a meeting bot (matches frontend vexaClient.stopBot).
    
    Args:
        platform: The meeting platform
        meeting_id: The native meeting ID
        
    Returns:
        Stop operation response
    """
    try:
        result = await stop_meeting_bot(meeting_id, platform)
        
        if not result["success"]:
            logger.error(f"Failed to stop bot: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vexa/meetings")
async def list_vexa_meetings():
    """
    List all meetings (matches frontend vexaClient.listMeetings).
    
    Returns:
        List of meetings
    """
    try:
        result = await list_meetings()
        
        if not result["success"]:
            logger.error(f"Failed to list meetings: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        # Return list directly for frontend compatibility
        meetings = result["data"]
        if isinstance(meetings, dict) and "meetings" in meetings:
            return meetings["meetings"]
        elif isinstance(meetings, list):
            return meetings
        else:
            return []
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing meetings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/vexa/meetings/{platform}/{meeting_id}")
async def update_vexa_meeting(platform: str, meeting_id: str, data: dict):
    """
    Update meeting metadata (matches frontend vexaClient.updateMeeting).
    
    Args:
        platform: The meeting platform
        meeting_id: The native meeting ID
        data: Meeting data to update
        
    Returns:
        Updated meeting response
    """
    try:
        result = await update_meeting_data(meeting_id, platform, data)
        
        if not result["success"]:
            logger.error(f"Failed to update meeting: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vexa/meetings/{platform}/{meeting_id}")
async def delete_vexa_meeting(platform: str, meeting_id: str):
    """
    Delete a meeting and its transcripts (matches frontend vexaClient.deleteMeeting).
    
    Args:
        platform: The meeting platform
        meeting_id: The native meeting ID
        
    Returns:
        Delete operation response
    """
    try:
        result = await delete_meeting(meeting_id, platform)
        
        if not result["success"]:
            logger.error(f"Failed to delete meeting: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/vexa/user/webhook")
async def set_vexa_webhook(webhook_data: dict):
    """
    Set webhook URL for the user (matches frontend vexaClient.setWebhook).
    
    Args:
        webhook_data: Contains webhook_url
        
    Returns:
        Webhook configuration response
    """
    try:
        webhook_url = webhook_data.get("webhook_url")
        if not webhook_url:
            raise HTTPException(status_code=400, detail="webhook_url is required")
            
        result = await set_webhook_url(webhook_url)
        
        if not result["success"]:
            logger.error(f"Failed to set webhook: {result.get('error')}")
            raise HTTPException(
                status_code=result.get('status_code', 500), 
                detail=result.get("error", "Unknown error")
            )
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add a vector database rebuild endpoint
@app.post("/api/vector-db/rebuild")
async def rebuild_vector_database():
    """
    Force a rebuild of the vector database from the knowledge files.
    This is useful when knowledge files have been updated and you want
    to refresh the embeddings without restarting the server.
    """
    try:
        logger.info("Rebuilding vector database...")
        # Use the file management API to rebuild
        await vector_db_manager._rebuild_index()
        stats = vector_db_manager.get_database_stats()
        total_chunks = stats.get('total_chunks', 0)
        return {
            "success": True,
            "chunks_processed": total_chunks,
            "message": f"Vector database rebuilt successfully with {total_chunks} chunks"
        }
    except Exception as e:
        logger.error(f"Error rebuilding vector database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/whisper-hotmic")
async def websocket_whisper_hotmic(websocket: WebSocket, language: str = None, model: str = "base"):
    """
    WebSocket endpoint for Whisper-based hot mic transcription with real-time sentence streaming.
    Provides immediate sentence-by-sentence transcription using OpenAI Whisper.
    
    Query Parameters:
        language: Language code for transcription (optional, auto-detect if None)
        model: Whisper model to use (tiny, base, small, medium, large)
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    logger.info(f"Whisper hot mic WebSocket connected: {connection_id}, model: {model}, language: {language}")
    
    # Import our transcription utilities
    from app.utils.transcription import process_streaming_audio
    
    # Create audio queue for processing
    audio_queue = asyncio.Queue()
    
    # Function to send results to client
    async def send_to_client(data):
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send data to client: {str(e)}")
    
    # Start Whisper transcription task
    transcription_task = asyncio.create_task(
        process_streaming_audio(
            audio_queue=audio_queue,
            send_to_client=send_to_client
        )
    )
    
    try:
        while True:
            try:
                # Receive audio data from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data and add to queue
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                    
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    logger.info("End of audio stream signal received")
                    await audio_queue.put(None)
                    break
                    
                elif message.get("type") == "config":
                    # Handle configuration changes
                    config = message.get("config", {})
                    await send_to_client({
                        "type": "config_updated",
                        "config": config,
                        "timestamp": time.time()
                    })
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {str(e)}")
                await send_to_client({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await send_to_client({
                    "type": "error",
                    "message": f"Processing error: {str(e)}",
                    "timestamp": time.time()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Whisper hot mic WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Whisper hot mic WebSocket error: {str(e)}")
    finally:
        # Cleanup
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                logger.info("Whisper transcription task cancelled")
        
        logger.info(f"Whisper hot mic WebSocket cleanup completed: {connection_id}")

@app.websocket("/ws/whisper-transcribe")
async def websocket_whisper_transcribe(websocket: WebSocket, language: str = None, model: str = "base"):
    """
    WebSocket endpoint for standard Whisper transcription with sentence segmentation.
    Processes audio in chunks and returns complete transcriptions with sentence breakdown.
    
    Query Parameters:
        language: Language code for transcription (optional, auto-detect if None)
        model: Whisper model to use (tiny, base, small, medium, large)
    """
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    logger.info(f"Whisper transcription WebSocket connected: {connection_id}, model: {model}, language: {language}")
    
    # Import our transcription utilities
    from app.utils.transcription import process_audio_stream
    
    # Create audio queue for processing
    audio_queue = asyncio.Queue()
    
    # Function to send results to client
    async def send_to_client(data):
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Failed to send data to client: {str(e)}")
    
    # Start Whisper transcription task
    transcription_task = asyncio.create_task(
        process_audio_stream(
            audio_queue=audio_queue,
            send_to_client=send_to_client
        )
    )
    
    try:
        while True:
            try:
                # Receive audio data from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "audio":
                    # Decode base64 audio data and add to queue
                    audio_data = base64.b64decode(message["data"])
                    await audio_queue.put(audio_data)
                    
                elif message.get("type") == "end":
                    # Signal end of audio stream
                    logger.info("End of audio stream signal received")
                    await audio_queue.put(None)
                    break
                    
                elif message.get("type") == "config":
                    # Handle configuration changes
                    config = message.get("config", {})
                    await send_to_client({
                        "type": "config_updated",
                        "config": config,
                        "timestamp": time.time()
                    })
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {str(e)}")
                await send_to_client({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await send_to_client({
                    "type": "error",
                    "message": f"Processing error: {str(e)}",
                    "timestamp": time.time()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Whisper transcription WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Whisper transcription WebSocket error: {str(e)}")
    finally:
        # Cleanup
        if connection_id in active_connections:
            del active_connections[connection_id]
        
        # Cancel transcription task if still running
        if not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                logger.info("Whisper transcription task cancelled")
        
        logger.info(f"Whisper transcription WebSocket cleanup completed: {connection_id}")

# Cache Management API Endpoints
@app.get("/api/cache/canonical-questions")
async def get_canonical_questions():
    """Get all canonical questions used for cache population"""
    try:
        # Get canonical questions from the data module
        canonical_questions = get_canonical_questions_list()
        
        # Also get existing cache entries to show what's already cached
        cache_entries = answer_cache.get_all_entries()
        cached_questions = []
        for entry in cache_entries:
            if isinstance(entry, dict) and 'question' in entry:
                cached_questions.append(entry['question'])
            elif isinstance(entry, str):
                cached_questions.append(entry)
        
        return {
            "questions": canonical_questions,
            "cached_questions": cached_questions,
            "total_canonical": len(canonical_questions),
            "total_cached": len(cached_questions),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting canonical questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get comprehensive cache statistics and performance metrics"""
    try:
        # Get cache statistics
        all_entries = answer_cache.get_all_entries()
        total_cached_questions = len(all_entries)
        
        # Calculate cache file size
        cache_file_path = "backend/app/uploads/cache_documents/answer_cache.json"
        cache_file_size = 0
        last_updated = None
        
        if os.path.exists(cache_file_path):
            cache_file_size = os.path.getsize(cache_file_path)
            # Get last modified time
            import datetime
            timestamp = os.path.getmtime(cache_file_path)
            last_updated = datetime.datetime.fromtimestamp(timestamp).isoformat()
        
        return {
            "cache_stats": {
                "total_cached_questions": total_cached_questions,
                "cache_file_size": cache_file_size,
                "last_updated": last_updated
            },
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/entries")
async def get_cache_entries(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None
):
    """Get paginated list of cache entries with optional search"""
    try:
        entries = answer_cache.get_all_entries()
        
        # Filter by search if provided
        if search:
            search_lower = search.lower()
            entries = [
                entry for entry in entries 
                if search_lower in entry.get('question', '').lower() or 
                   search_lower in entry.get('answer', '').lower()
            ]
        
        # Paginate results
        total = len(entries)
        paginated_entries = entries[offset:offset + limit]
        
        return {
            "entries": paginated_entries,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error(f"Error getting cache entries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class CacheEntryUpdate(BaseModel):
    question: str
    answer: str
    confidence: Optional[float] = None

@app.put("/api/cache/entries/{entry_id}")
async def update_cache_entry(entry_id: str, update_data: CacheEntryUpdate):
    """Update a specific cache entry"""
    try:
        # Update the entry in cache
        updated = answer_cache.update_entry(
            entry_id,
            update_data.question,
            update_data.answer,
            update_data.confidence
        )
        
        if not updated:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        return {
            "success": True,
            "message": "Cache entry updated successfully",
            "entry_id": entry_id
        }
    except Exception as e:
        logger.error(f"Error updating cache entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cache/entries/{entry_id}")
async def delete_cache_entry(entry_id: str):
    """Delete a specific cache entry"""
    try:
        deleted = answer_cache.delete_entry(entry_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Cache entry not found")
        
        return {
            "success": True,
            "message": "Cache entry deleted successfully",
            "entry_id": entry_id
        }
    except Exception as e:
        logger.error(f"Error deleting cache entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    try:
        answer_cache.clear_cache()
        return {
            "success": True,
            "message": "Cache cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/optimize")
async def optimize_cache():
    """Optimize cache by removing old or low-confidence entries"""
    try:
        removed_count = answer_cache.optimize_cache()
        return {
            "success": True,
            "message": f"Cache optimized successfully. Removed {removed_count} entries.",
            "removed_entries": removed_count
        }
    except Exception as e:
        logger.error(f"Error optimizing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class CacheConfigUpdate(BaseModel):
    max_entries: Optional[int] = None
    confidence_threshold: Optional[float] = None
    similarity_threshold: Optional[float] = None

@app.put("/api/cache/config")
async def update_cache_config(config: CacheConfigUpdate):
    """Update cache configuration settings"""
    try:
        updated_config = answer_cache.update_config(
            max_entries=config.max_entries,
            confidence_threshold=config.confidence_threshold,
            similarity_threshold=config.similarity_threshold
        )
        
        return {
            "success": True,
            "message": "Cache configuration updated successfully",
            "config": updated_config
        }
    except Exception as e:
        logger.error(f"Error updating cache config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/config")
async def get_cache_config():
    """Get current cache configuration settings"""
    try:
        config = answer_cache.get_config()
        return config
    except Exception as e:
        logger.error(f"Error getting cache config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class BulkCacheEntry(BaseModel):
    question: str
    answer: str
    confidence: Optional[float] = 1.0

@app.post("/api/cache/bulk-add")
async def bulk_add_cache_entries(entries: List[BulkCacheEntry]):
    """Add multiple cache entries in bulk"""
    try:
        added_count = 0
        errors = []
        
        for i, entry in enumerate(entries):
            try:
                answer_cache.store_answer(
                    entry.question,
                    entry.answer,
                    entry.confidence or 1.0
                )
                added_count += 1
            except Exception as e:
                errors.append({
                    "index": i,
                    "question": entry.question[:50] + "..." if len(entry.question) > 50 else entry.question,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Successfully added {added_count} out of {len(entries)} entries",
            "added_count": added_count,
            "total_count": len(entries),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error bulk adding cache entries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cache/search")
async def search_cache(
    query: str,
    limit: int = 10,
    confidence_threshold: float = 0.7
):
    """Search cache entries by semantic similarity"""
    try:
        # Use the cache's search functionality
        results = answer_cache.search_similar(query, limit, confidence_threshold)
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/backup")
async def backup_cache():
    """Create a backup of the current cache"""
    try:
        backup_path = answer_cache.create_backup()
        return {
            "success": True,
            "message": "Cache backup created successfully",
            "backup_path": backup_path,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error creating cache backup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/restore")
async def restore_cache(backup_file: str):
    """Restore cache from a backup file"""
    try:
        restored = answer_cache.restore_from_backup(backup_file)
        
        if not restored:
            raise HTTPException(status_code=404, detail="Backup file not found")
        
        return {
            "success": True,
            "message": "Cache restored successfully from backup",
            "backup_file": backup_file
        }
    except Exception as e:
        logger.error(f"Error restoring cache: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/batch-refresh")
async def batch_refresh_cache(request: Request):
    """Refresh cache by re-processing canonical questions through the analyze endpoint"""
    try:
        # Import here to avoid circular imports
        import asyncio
        import httpx
        from app.models import ConversationAnalysisRequest
        
        # Get current cache entries that could be considered canonical
        all_entries = answer_cache.get_all_entries()
        canonical_questions = [
            entry['question'] for entry in all_entries 
            if entry.get('confidence', 0) >= 0.7  # Only refresh high-confidence entries
        ]
        
        if not canonical_questions:
            return {
                "success": True,
                "message": "No canonical questions found to refresh",
                "summary": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "errors": []
                }
            }
        
        # Process questions through the analyze endpoint
        successful = 0
        failed = 0
        errors = []
        
        # Get base URL from request
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, question in enumerate(canonical_questions[:20]):  # Limit to 20 to avoid timeouts
                try:
                    # Call our own analyze endpoint to get fresh responses
                    response = await client.post(
                        f"{base_url}/analyze",
                        json={
                            "conversation": question,
                            "max_response_length": 500,
                            "tone": "professional",
                            "include_sources": True,
                            "include_web_search": False,  # Skip web search for batch refresh
                            "detect_gaps": True
                        }
                    )
                    
                    if response.status_code == 200:
                        # The analyze endpoint automatically updates the cache
                        successful += 1
                        logger.info(f"Refreshed cache for question {i+1}/{len(canonical_questions)}")
                    else:
                        failed += 1
                        error_msg = f"HTTP {response.status_code} for question: {question[:50]}..."
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    failed += 1
                    error_msg = f"Error refreshing '{question[:50]}...': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.5)
        
        return {
            "success": True,
            "message": f"Batch refresh completed. {successful} successful, {failed} failed.",
            "summary": {
                "total": len(canonical_questions),
                "successful": successful,
                "failed": failed,
                "errors": errors[:10]  # Limit error list to prevent huge responses
            }
        }
        
    except Exception as e:
        logger.error(f"Error during batch cache refresh: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/update")
async def update_cache_missing_entries(request: Request):
    """
    Intelligently update cache by checking for missing entries and only generating
    responses for questions that aren't already cached with good confidence.
    """
    try:
        # Import here to avoid circular imports
        import asyncio
        import httpx
        
        # Define canonical questions (you might want to load these from a file)
        canonical_questions = get_canonical_questions_list()
        
        # Check which questions are missing from cache or have low confidence
        missing_questions = []
        existing_entries = answer_cache.get_all_entries()
        
        # Create a map of existing questions with their confidence scores
        existing_map = {}
        for entry in existing_entries:
            if isinstance(entry, dict) and 'question' in entry:
                question = entry['question'].lower().strip()
                confidence = entry.get('confidence', 0)
                existing_map[question] = confidence
        
        # Find missing or low-confidence questions
        confidence_threshold = 0.7
        for question in canonical_questions:
            question_key = question.lower().strip()
            if question_key not in existing_map or existing_map[question_key] < confidence_threshold:
                missing_questions.append(question)
        
        if not missing_questions:
            return {
                "success": True,
                "message": "All canonical questions are already cached with good confidence",
                "summary": {
                    "total_canonical": len(canonical_questions),
                    "already_cached": len(canonical_questions),
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "errors": []
                }
            }
        
        logger.info(f"Found {len(missing_questions)} questions to process out of {len(canonical_questions)} canonical questions")
        
        # Process missing questions through the analyze endpoint
        successful = 0
        failed = 0
        errors = []
        
        # Get base URL from request
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, question in enumerate(missing_questions):
                try:
                    logger.info(f"Processing question {i+1}/{len(missing_questions)}: {question[:50]}...")
                    
                    # Call our own analyze endpoint to get fresh responses
                    response = await client.post(
                        f"{base_url}/analyze",
                        json={
                            "conversation": question,
                            "max_response_length": 400,
                            "tone": "professional",
                            "include_sources": True,
                            "include_web_search": False,  # Skip web search for faster processing
                            "detect_gaps": False  # Skip gap detection for canonical questions
                        }
                    )
                    
                    if response.status_code == 200:
                        # The analyze endpoint automatically updates the cache
                        successful += 1
                        logger.info(f"Successfully cached question {i+1}/{len(missing_questions)}")
                    else:
                        failed += 1
                        error_msg = f"HTTP {response.status_code} for question: {question[:50]}..."
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    failed += 1
                    error_msg = f"Error processing '{question[:50]}...': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.3)
        
        return {
            "success": True,
            "message": f"Cache update completed. {successful} new entries added, {failed} failed.",
            "summary": {
                "total_canonical": len(canonical_questions),
                "already_cached": len(canonical_questions) - len(missing_questions),
                "processed": len(missing_questions),
                "successful": successful,
                "failed": failed,
                "errors": errors[:5]  # Limit error list
            }
        }
        
    except Exception as e:
        logger.error(f"Error during cache update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))