"""
OpenAI client utilities for conversation analysis
"""
import json
import logging
import time
from typing import Dict, Any, Optional
import openai

from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    MAX_RESPONSE_LENGTH,
    DEFAULT_TONE
)
from app.prompts import OPENAI_CLIENT_SYSTEM_PROMPT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

async def analyze_conversation(
    conversation: str,
    max_response_length: Optional[int] = None,
    tone: Optional[str] = None,
    include_sources: Optional[bool] = False
) -> Dict[str, Any]:
    """Analyze a conversation snippet and provide an AI-generated response."""
    
    # Start timer for response time tracking
    start_time = time.time()
    
    # Use default tone if none provided
    tone = tone or DEFAULT_TONE
    
    try:
        # Set default max response length if not provided
        if max_response_length is None:
            max_response_length = MAX_RESPONSE_LENGTH
            
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": OPENAI_CLIENT_SYSTEM_PROMPT.format(tone=tone)},
                {"role": "user", "content": f"""Conversation snippet: {conversation}

Analyze this conversation and provide a comprehensive response. Return your response as a JSON object with the following structure:

{{
    "intent": "Brief description of what the customer wants",
    "question": "Main question being asked (if any)",
    "information_gap": "What information is missing or needed",
    "straightforward_answer": "Direct answer to the question",
    "response": "Detailed response to the conversation",
    "sentiment": "neutral/positive/negative",
    "statistics": {{"stat1": "value1", "stat2": "value2"}}, 
    "salesPoints": ["point1", "point2", "point3"],
    "relevant_bullets": ["bullet1", "bullet2", "bullet3"],
    "escalation_flag": false,
    "follow_up_questions": ["question1", "question2"],
    "meta": {{"confidence": 0.9, "sources": ["source1"]}}
}}

Ensure statistics is returned as a dictionary with descriptive keys and values."""}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        response_content = response.choices[0].message.content
        result = json.loads(response_content)
        
        # Ensure all required fields are present with defaults
        result.setdefault("intent", "general_inquiry")
        result.setdefault("question", None)
        result.setdefault("information_gap", "")
        result.setdefault("straightforward_answer", result.get("response", ""))
        result.setdefault("response", "")
        result.setdefault("sentiment", "neutral")
        result.setdefault("statistics", {})
        result.setdefault("salesPoints", [])
        result.setdefault("relevant_bullets", result.get("salesPoints", []))
        result.setdefault("escalation_flag", False)
        result.setdefault("follow_up_questions", [])
        result.setdefault("meta", {})
        
        # Ensure statistics is a dictionary
        if isinstance(result["statistics"], list):
            # Convert list to dictionary with numbered keys
            stats_dict = {}
            for i, stat in enumerate(result["statistics"], 1):
                stats_dict[f"metric_{i}"] = stat
            result["statistics"] = stats_dict
        
        # Truncate response if needed
        if max_response_length and len(result["response"]) > max_response_length:
            result["response"] = result["response"][:max_response_length] + "..."
        
        # Add response time to metadata
        result["meta"]["response_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        return {
            "intent": "error",
            "question": None,
            "information_gap": "Unable to analyze the conversation due to an error",
            "straightforward_answer": "I'm sorry, I encountered an error while analyzing the conversation.",
            "response": "I'm sorry, I encountered an error while analyzing the conversation.",
            "sentiment": "neutral",
            "statistics": {},
            "salesPoints": [],
            "relevant_bullets": [],
            "escalation_flag": False,
            "follow_up_questions": [],
            "meta": {"error": str(e)}
        }
