"""
Vexa API client utility for managing meetings and transcripts.
"""
import httpx
import logging
from typing import Dict, Any, Optional, List
import json
import uuid
import time
import random
import asyncio
from app.config import VEXA_API_KEY, VEXA_BASE_URL

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
MOCK_MODE = False  # Enable/disable mock mode - SET TO FALSE FOR REAL API
MAX_RETRIES = 3    # Maximum number of retry attempts
RETRY_DELAY = 1.0  # Initial delay between retries in seconds (will be exponentially increased)

# Mock data for testing
MOCK_MEETINGS = {}
MOCK_TRANSCRIPTS = {}

# Configure retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds between retries

# Sample speakers and phrases for generating mock transcripts
MOCK_SPEAKERS = ["John", "Lisa", "Michael", "Sarah", "David", "Alex", "Emma", "Robert"]
MOCK_PHRASES = [
    "I think we should focus on the customer experience for this quarter.",
    "What about our quarterly goals and targets? Are we on track?",
    "The new product launch is scheduled for next month. We need to finalize the marketing materials.",
    "I agree with that assessment. Let's move forward with this approach.",
    "Let me share my screen to show you the data I've been analyzing.",
    "We need to improve our marketing strategy based on the recent customer feedback.",
    "Can everyone see my screen? I want to show you the latest design mockups.",
    "Let's discuss the budget for next quarter and allocate resources accordingly.",
    "I have a question about the timeline for the implementation phase.",
    "That's a great point, thanks for bringing it up. I hadn't considered that perspective.",
    "We should prioritize fixing the critical bugs before adding new features.",
    "The user research indicates that customers prefer the simplified interface.",
    "I'm concerned about the timeline. Can we realistically deliver by the deadline?",
    "Let's schedule a follow-up meeting to dive deeper into these technical details.",
    "I propose we create a small team to focus specifically on this problem."
]

async def mock_vexa_api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Mock implementation of Vexa API requests for testing.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: The data to send in the request body for POST/PUT
        params: Query parameters for GET requests
        
    Returns:
        Mock response data
    """
    # Handle joining a meeting
    if method == "POST" and endpoint == "/bots":
        meeting_id = str(uuid.uuid4())
        
        # Store meeting info
        MOCK_MEETINGS[meeting_id] = {
            "id": meeting_id,
            "native_meeting_id": data["native_meeting_id"],
            "platform": data["platform"],
            "bot_name": data.get("bot_name", "SalesAssistBot"),
            "created_at": time.time()
        }
        
        # Initialize empty transcript list
        MOCK_TRANSCRIPTS[meeting_id] = []
        
        # Generate some initial transcripts
        for i in range(3):
            transcript_id = str(uuid.uuid4())
            speaker = random.choice(MOCK_SPEAKERS)
            text = random.choice(MOCK_PHRASES)
            
            MOCK_TRANSCRIPTS[meeting_id].append({
                "id": transcript_id,
                "meeting_id": meeting_id,
                "speaker": speaker,
                "text": text,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "confidence": random.uniform(0.7, 0.98)
            })
        
        return {
            "success": True,
            "data": {
                "bot": {
                    "id": meeting_id,
                    "native_meeting_id": data["native_meeting_id"],
                    "platform": data["platform"],
                    "status": "joined",
                    "bot_name": data.get("bot_name", "SalesAssistBot")
                }
            }
        }
    
    # Handle getting transcripts
    elif method == "GET" and endpoint.startswith("/transcripts/"):
        # Extract platform and meeting ID from endpoint - format: /transcripts/{platform}/{meeting_id}
        parts = endpoint.split("/")
        if len(parts) >= 4:
            platform = parts[2]
            meeting_id = parts[3]
        else:
            return {
                "success": False,
                "error": f"Invalid endpoint format: {endpoint}"
            }
            
        # Find a meeting that matches the platform and meeting_id
        matching_meeting = None
        for mid, meeting_data in MOCK_MEETINGS.items():
            if (meeting_data.get("platform") == platform and 
                meeting_data.get("native_meeting_id") == meeting_id):
                matching_meeting = mid
                break
                
        if not matching_meeting:
            return {
                "success": False,
                "error": f"No active bot found for {platform}/{meeting_id}"
            }
            
        # Use the meeting ID we found
        meeting_id = matching_meeting
            
        if meeting_id not in MOCK_TRANSCRIPTS:
            return {
                "success": False,
                "error": f"Bot {meeting_id} not found"
            }
        
        # Add a new transcript entry each time this is called
        if random.random() > 0.3:  # 70% chance of new transcript
            # Create 1-3 new transcript entries to simulate real conversation
            num_new_entries = random.randint(1, 3)
            
            for _ in range(num_new_entries):
                transcript_id = str(uuid.uuid4())
                speaker = random.choice(MOCK_SPEAKERS)
                text = random.choice(MOCK_PHRASES)
                
                # Add timestamp with increasing time
                current_time = time.gmtime(time.time() + len(MOCK_TRANSCRIPTS[meeting_id]) * 5)
                timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", current_time)
                
                MOCK_TRANSCRIPTS[meeting_id].append({
                    "id": transcript_id,
                    "meeting_id": meeting_id,
                    "speaker": speaker,
                    "text": text,
                    "timestamp": timestamp,
                    "confidence": random.uniform(0.7, 0.98)
                })
        
        # Get the platform from the stored meeting data
        platform = MOCK_MEETINGS.get(meeting_id, {}).get("platform", "unknown")
        
        return {
            "success": True,
            "data": {
                "bot": {
                    "id": meeting_id,
                    "platform": platform,
                    "status": "active"
                },
                "transcripts": MOCK_TRANSCRIPTS[meeting_id]
            }
        }
    
    # Handle leaving a meeting
    elif method == "DELETE" and endpoint.startswith("/bots/"):
        # Extract platform and meeting ID from endpoint - format: /bots/{platform}/{meeting_id}
        parts = endpoint.split("/")
        if len(parts) >= 4:
            platform = parts[2]
            native_meeting_id = parts[3]
        else:
            return {
                "success": False,
                "error": f"Invalid endpoint format: {endpoint}"
            }
            
        # Find a meeting that matches the platform and meeting_id
        matching_meeting = None
        for mid, meeting_data in MOCK_MEETINGS.items():
            if (meeting_data.get("platform") == platform and 
                meeting_data.get("native_meeting_id") == native_meeting_id):
                matching_meeting = mid
                break
                
        if not matching_meeting:
            return {
                "success": False,
                "error": f"No active bot found for {platform}/{native_meeting_id}"
            }
            
        # Use the meeting ID we found
        meeting_id = matching_meeting
        
        if meeting_id not in MOCK_MEETINGS:
            return {
                "success": False,
                "error": f"Bot {meeting_id} not found"
            }
        
        # Remove meeting and transcripts
        MOCK_MEETINGS.pop(meeting_id, None)
        MOCK_TRANSCRIPTS.pop(meeting_id, None)
        
        return {
            "success": True,
            "data": {
                "bot": {
                    "id": meeting_id,
                    "status": "removed"
                }
            }
        }
    
    # Handle getting bot status
    elif method == "GET" and endpoint == "/bots/status":
        active_bots = []
        for meeting_id, meeting_data in MOCK_MEETINGS.items():
            active_bots.append({
                "id": meeting_id,
                "native_meeting_id": meeting_data.get("native_meeting_id"),
                "platform": meeting_data.get("platform"),
                "bot_name": meeting_data.get("bot_name"),
                "status": "active",
                "created_at": meeting_data.get("created_at")
            })
        
        return {
            "success": True,
            "data": {
                "active_bots": active_bots,
                "total_count": len(active_bots)
            }
        }
    
    # Handle listing meetings
    elif method == "GET" and endpoint == "/meetings":
        meetings = []
        for meeting_id, meeting_data in MOCK_MEETINGS.items():
            meetings.append({
                "id": meeting_id,
                "native_meeting_id": meeting_data.get("native_meeting_id"),
                "platform": meeting_data.get("platform"),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(meeting_data.get("created_at", time.time()))),
                "status": "active",
                "data": {
                    "name": f"Meeting {meeting_data.get('native_meeting_id')}",
                    "participants": ["John", "Sarah", "Mike", "Lisa"],
                    "languages": ["en"]
                }
            })
        
        return {
            "success": True,
            "data": meetings
        }

    # Handle unknown endpoints
    return {
        "success": False,
        "error": f"Mock API: Unsupported endpoint {endpoint} or method {method}"
    }

async def vexa_api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retry: bool = True
) -> Dict[str, Any]:
    """
    Make a request to the Vexa API with automatic retry for transient errors.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: The data to send in the request body for POST/PUT
        params: Query parameters for GET requests
        timeout: Request timeout in seconds
        retry: Whether to retry on failure
        
    Returns:
        Response data as dictionary
    """
    # If mock mode is enabled, use mock implementation
    if MOCK_MODE:
        return await mock_vexa_api_request(method, endpoint, data, params)
    
    # Otherwise, use real API
    url = f"{VEXA_BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": VEXA_API_KEY
    }
    
    logger.info(f"Making Vexa API request: {method} {url}")
    
    retries = MAX_RETRIES if retry else 0
    attempt = 0
    last_error = None
    
    while attempt <= retries:
        attempt += 1
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=timeout
                    )
                elif method.upper() == "POST":
                    response = await client.post(
                        url,
                        json=data,
                        headers=headers,
                        timeout=timeout
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url,
                        json=data,
                        headers=headers,
                        timeout=timeout
                    )
                elif method.upper() == "DELETE":
                    response = await client.delete(
                        url,
                        headers=headers,
                        timeout=timeout
                    )
                else:
                    return {"success": False, "error": f"Unsupported HTTP method: {method}"}
                
                response.raise_for_status()
                return {"success": True, "data": response.json()}
                
        except httpx.HTTPStatusError as e:
            last_error = e
            error_msg = f"HTTP error occurred: {e.response.status_code}"
            logger.error(f"{error_msg}. Response: {e.response.text}")
            
            # Only retry on server errors (5xx) and some specific status codes
            if 500 <= e.response.status_code < 600 or e.response.status_code in [429]:
                if attempt <= retries:
                    wait_time = RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s... (Attempt {attempt}/{retries})")
                    await asyncio.sleep(wait_time)
                    continue
            
            # For client errors or after max retries, return error
            return {
                "success": False,
                "error": error_msg,
                "details": e.response.text
            }
            
        except httpx.ConnectError as e:
            last_error = e
            error_msg = f"Connection error occurred: {str(e)}"
            logger.error(error_msg)
            
            if attempt <= retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(f"Retrying in {wait_time}s... (Attempt {attempt}/{retries})")
                await asyncio.sleep(wait_time)
                continue
                
            return {"success": False, "error": error_msg, "is_connection_error": True}
            
        except httpx.RequestError as e:
            last_error = e
            error_msg = f"Request error occurred: {str(e)}"
            logger.error(error_msg)
            
            if attempt <= retries:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                logger.info(f"Retrying in {wait_time}s... (Attempt {attempt}/{retries})")
                await asyncio.sleep(wait_time)
                continue
                
            return {"success": False, "error": error_msg}
            
        except json.JSONDecodeError:
            last_error = "JSON decode error"
            error_msg = "Failed to parse JSON response"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            last_error = e
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    # If we get here, we've exhausted our retries
    return {"success": False, "error": f"Failed after {retries} retries. Last error: {str(last_error)}"}

async def join_meeting(native_meeting_id: str, platform: str) -> Dict[str, Any]:
    """
    Add Vexa bot to a meeting.
    
    Args:
        native_meeting_id: The meeting ID from the platform (Google Meet, etc.)
        platform: The platform name (google_meet, zoom, teams)
        
    Returns:
        Response with meeting ID and status
    """
    data = {
        "platform": platform,
        "native_meeting_id": native_meeting_id,
        "bot_name": "SalesAssistBot"  # Add a default bot name
    }
    
    return await vexa_api_request("POST", "/bots", data=data)

async def request_meeting_bot(native_meeting_id: str, platform: str = "google_meet", language: str = "en", bot_name: str = "Spiked AI Bot") -> Dict[str, Any]:
    """
    Request a Vexa bot for a meeting.
    
    Args:
        native_meeting_id: The meeting ID from the platform
        platform: The platform name (google_meet, zoom, teams)
        language: The language for transcription
        bot_name: The name for the bot
        
    Returns:
        Response with meeting ID and status
    """
    data = {
        "platform": platform,
        "native_meeting_id": native_meeting_id,
        "language": language,
        "bot_name": bot_name
    }
    
    return await vexa_api_request("POST", "/bots", data=data)

async def get_meeting_transcript(meeting_id: str, platform: str = "google_meet") -> Dict[str, Any]:
    """
    Get real-time meeting transcript.
    
    Args:
        meeting_id: The meeting ID
        platform: The platform name (google_meet, zoom, teams)
        
    Returns:
        Meeting transcript data
    """
    return await vexa_api_request("GET", f"/transcripts/{platform}/{meeting_id}", retry=False)

async def get_bot_status() -> Dict[str, Any]:
    """
    Get status of running bots.
    
    Returns:
        Status of all running bots
    """
    return await vexa_api_request("GET", "/bots/status")

async def update_bot_config(meeting_id: str, platform: str = "google_meet", config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update bot configuration.
    
    Args:
        meeting_id: The meeting ID
        platform: The platform name
        config: Configuration to update
        
    Returns:
        Updated configuration response
    """
    return await vexa_api_request("PUT", f"/bots/{platform}/{meeting_id}/config", data=config)

async def stop_meeting_bot(meeting_id: str, platform: str = "google_meet") -> Dict[str, Any]:
    """
    Stop a meeting bot.
    
    Args:
        meeting_id: The meeting ID
        platform: The platform name
        
    Returns:
        Stop operation response
    """
    return await vexa_api_request("DELETE", f"/bots/{platform}/{meeting_id}")

async def list_meetings() -> Dict[str, Any]:
    """
    List all meetings.
    
    Returns:
        List of meetings
    """
    return await vexa_api_request("GET", "/meetings")

async def update_meeting_data(meeting_id: str, platform: str = "google_meet", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update meeting metadata.
    
    Args:
        meeting_id: The meeting ID
        platform: The platform name
        data: Meeting data to update
        
    Returns:
        Updated meeting response
    """
    return await vexa_api_request("PATCH", f"/meetings/{platform}/{meeting_id}", data=data)

async def delete_meeting(meeting_id: str, platform: str = "google_meet") -> Dict[str, Any]:
    """
    Delete a meeting and its transcripts.
    
    Args:
        meeting_id: The meeting ID
        platform: The platform name
        
    Returns:
        Delete operation response
    """
    return await vexa_api_request("DELETE", f"/meetings/{platform}/{meeting_id}")

async def set_webhook_url(webhook_url: str) -> Dict[str, Any]:
    """
    Set webhook URL for the user.
    
    Args:
        webhook_url: The webhook URL to set
        
    Returns:
        Webhook configuration response
    """
    data = {"webhook_url": webhook_url}
    return await vexa_api_request("PUT", "/user/webhook", data=data)

async def get_meeting_transcripts(platform: str, meeting_id: str) -> Dict[str, Any]:
    """
    Get transcripts from a meeting.
    
    Args:
        platform: The platform name (google_meet, zoom, teams)
        meeting_id: The meeting ID
        
    Returns:
        List of transcripts from the meeting
    """
    # Don't retry for transcript fetching to avoid slowing down the UI
    return await vexa_api_request("GET", f"/transcripts/{platform}/{meeting_id}", params=None, retry=False)

async def leave_meeting(platform: str, meeting_id: str) -> Dict[str, Any]:
    """
    Remove Vexa bot from a meeting.
    
    Args:
        platform: The platform name (google_meet, zoom, teams)
        meeting_id: The meeting ID
        
    Returns:
        Status of the leave operation
    """
    return await vexa_api_request("DELETE", f"/bots/{platform}/{meeting_id}", data=None)
