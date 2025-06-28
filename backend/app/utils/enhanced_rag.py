"""
Enhanced RAG (Retrieval-Augmented Generation) implementation for conversation analysis.
This module provides comprehensive document-aware conversation analysis with structured responses.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional

import openai
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.prompts import ENHANCED_RAG_SYSTEM_PROMPT, DEFAULT_TONE
from app.utils.vector_db_manager import VectorDBManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize vector database manager
vector_db = VectorDBManager()

# Default response length
MAX_RESPONSE_LENGTH = 500


def extract_health_assist_context(sources: List[Dict[str, Any]]) -> Dict[str, str]:
    """Extract specific HealthAssist context from sources for better responses."""
    context_data = {
        "pricing_info": "",
        "technical_specs": "",
        "implementation": "",
        "use_cases": "",
        "compliance": "",
        "integration": ""
    }
    
    for source in sources:
        content = source.get("content", "").lower()
        source_info = source.get("source_info", {})
        filename = source_info.get("filename", "").lower()
        
        # Extract pricing information
        if any(keyword in content for keyword in ["price", "cost", "subscription", "license", "billing"]):
            context_data["pricing_info"] += f" {source['content']}"
        
        # Extract technical specifications
        if any(keyword in content for keyword in ["api", "integration", "technical", "sdk", "configuration"]):
            context_data["technical_specs"] += f" {source['content']}"
        
        # Extract implementation details
        if any(keyword in content for keyword in ["implementation", "deployment", "setup", "install"]):
            context_data["implementation"] += f" {source['content']}"
        
        # Extract use cases
        if any(keyword in content for keyword in ["use case", "example", "scenario", "customer"]):
            context_data["use_cases"] += f" {source['content']}"
        
        # Extract compliance information
        if any(keyword in content for keyword in ["compliance", "security", "gdpr", "soc", "hipaa"]):
            context_data["compliance"] += f" {source['content']}"
        
        # Extract integration details
        if any(keyword in content for keyword in ["integration", "connect", "webhook", "bot"]):
            context_data["integration"] += f" {source['content']}"
    
    # Clean up and truncate
    for key in context_data:
        context_data[key] = context_data[key].strip()[:1000] if context_data[key] else ""
    
    return context_data


def build_contextual_prompt(conversation: str, sources: List[Dict[str, Any]], tone: str) -> str:
    """Build a comprehensive contextual prompt with relevant document sources."""
    
    # Extract structured context
    health_context = extract_health_assist_context(sources)
    
    # Build source context string
    source_context = ""
    if sources:
        source_context = "\n\nRELEVANT KNOWLEDGE SOURCES:\n"
        for i, source in enumerate(sources[:5], 1):  # Limit to top 5 sources
            source_info = source.get("source_info", {})
            filename = source_info.get("filename", "Unknown")
            chunk_num = source_info.get("chunk_number", 1)
            similarity = source.get("similarity_score", 0)
            
            source_context += f"\nSource {i} ({filename}, chunk {chunk_num}, relevance: {similarity:.2f}):\n"
            source_context += f"{source['content'][:500]}...\n"
    
    # Build specialized context sections
    specialized_context = ""
    if health_context["pricing_info"]:
        specialized_context += f"\nPRICING CONTEXT:\n{health_context['pricing_info'][:300]}...\n"
    
    if health_context["technical_specs"]:
        specialized_context += f"\nTECHNICAL CONTEXT:\n{health_context['technical_specs'][:300]}...\n"
    
    if health_context["use_cases"]:
        specialized_context += f"\nUSE CASES CONTEXT:\n{health_context['use_cases'][:300]}...\n"
    
    if health_context["compliance"]:
        specialized_context += f"\nCOMPLIANCE CONTEXT:\n{health_context['compliance'][:300]}...\n"
    
    # Build the full prompt
    full_prompt = f"""CUSTOMER CONVERSATION:
{conversation}

ANALYSIS CONTEXT:{source_context}{specialized_context}

IMPORTANT GUIDELINES:
1. Base your response strictly on the provided context sources
2. If pricing information is mentioned in sources, include it in pricing_insight
3. Use technical terms found in the sources and explain them in terminology_explainer
4. Extract real statistics and metrics from the sources for the statistics field
5. Create relevant bullets from source content, not generic sales points
6. Use customer examples from sources for customer_story_snippet
7. Generate follow-up questions based on BANT C methodology and the conversation context
8. Set escalation_flag to true if the question requires specialized expertise or pricing approval
9. Extract real company/product names and use cases from the sources

Your response must be relevant to HealthAssist, Kore.ai, and the conversation analysis domain based on the sources provided."""

    return full_prompt


async def enhanced_rag_analyze(
    conversation: str,
    max_response_length: Optional[int] = None,
    tone: Optional[str] = None,
    include_sources: Optional[bool] = True
) -> Dict[str, Any]:
    """
    Enhanced RAG-based conversation analysis using vector search and document context.
    
    Args:
        conversation: The conversation snippet to analyze
        max_response_length: Maximum length for responses
        tone: Tone for the response (professional, friendly, etc.)
        include_sources: Whether to include source information
        
    Returns:
        Dict containing structured analysis with all enhanced fields
    """
    start_time = time.time()
    
    # Set defaults
    tone = tone or DEFAULT_TONE
    max_response_length = max_response_length or MAX_RESPONSE_LENGTH
    
    try:
        # Step 1: Retrieve relevant documents using vector search
        relevant_sources = []
        if include_sources:
            try:
                relevant_sources = await vector_db.search_similar_chunks(
                    query=conversation,
                    k=8  # Get top 8 most relevant chunks
                )
                logger.info(f"Retrieved {len(relevant_sources)} relevant sources from vector DB")
            except Exception as e:
                logger.warning(f"Vector search failed: {e}, proceeding without sources")
        
        # Step 2: Build contextual prompt with document sources
        contextual_prompt = build_contextual_prompt(conversation, relevant_sources, tone)
        
        # Step 3: Generate enhanced response using OpenAI
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": ENHANCED_RAG_SYSTEM_PROMPT.format(tone=tone)},
                {"role": "user", "content": contextual_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        response_content = response.choices[0].message.content
        result = json.loads(response_content)
        
        # Step 4: Ensure all required fields are present and properly formatted
        enhanced_result = {
            # Basic fields
            "intent": result.get("intent", "general_inquiry"),
            "question": result.get("question"),
            "information_gap": result.get("information_gap", ""),
            
            # Core answer
            "straightforward_answer": result.get("straightforward_answer", ""),
            "response": result.get("straightforward_answer", ""),  # Legacy compatibility
            
            # Enhanced structured fields
            "star_response": format_star_response(result.get("star_response")),
            "comparison_table": format_comparison_table(result.get("comparison_table")),
            "relevant_bullets": result.get("relevant_bullets", [])[:15],  # Limit to 15
            "statistics": ensure_statistics_dict(result.get("statistics", {})),
            "terminology_explainer": format_terminology_explainer(result.get("terminology_explainer")),
            "analogies_or_metaphors": format_analogies_metaphors(result.get("analogies_or_metaphors")),
            "customer_story_snippet": format_customer_story(result.get("customer_story_snippet")),
            "pricing_insight": format_pricing_insight(result.get("pricing_insight")),
            
            # Control fields
            "escalation_flag": result.get("escalation_flag", False),
            "follow_up_questions": result.get("follow_up_questions", [])[:5],  # Limit to 5
            
            # Legacy fields
            "sentiment": result.get("sentiment", "neutral"),
            "salesPoints": result.get("relevant_bullets", [])[:10],  # Legacy compatibility
            "longform_response": result.get("longform_response", ""),
            
            # Metadata
            "meta": {
                "sources": [source.get("source_info", {}) for source in relevant_sources[:3]],
                "source_count": len(relevant_sources),
                "confidence": calculate_confidence_score(result, relevant_sources),
                "response_time_ms": int((time.time() - start_time) * 1000),
                "model_used": OPENAI_MODEL,
                "vector_search_enabled": include_sources and len(relevant_sources) > 0
            }
        }
        
        # Step 5: Apply response length limit
        if max_response_length and len(enhanced_result["response"]) > max_response_length:
            enhanced_result["response"] = enhanced_result["response"][:max_response_length] + "..."
            enhanced_result["straightforward_answer"] = enhanced_result["straightforward_answer"][:max_response_length] + "..."
        
        logger.info(f"Enhanced RAG analysis completed in {enhanced_result['meta']['response_time_ms']}ms")
        return enhanced_result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return create_error_response("Failed to parse AI response", start_time)
    except Exception as e:
        logger.error(f"Enhanced RAG analysis error: {e}")
        return create_error_response(str(e), start_time)


def format_star_response(star_data: Any) -> Optional[Dict[str, Any]]:
    """Format STAR response according to model structure with enhanced validation."""
    if not star_data or not isinstance(star_data, dict):
        return None
    
    status = star_data.get("status", "not_required")
    if status not in ["required", "not_required"]:
        status = "not_required"
    
    if status == "required" and star_data.get("value"):
        value = star_data["value"]
        
        # If value is a string, keep it as is for parsing on frontend
        if isinstance(value, str):
            return {
                "status": status,
                "value": value
            }
        
        # If value is an object, validate structure
        elif isinstance(value, dict):
            # Ensure all STAR components are present and properly formatted
            formatted_value = {}
            
            for key in ["situation", "task", "action", "result"]:
                if value.get(key):
                    formatted_value[key] = str(value[key]).strip()
            
            # Only return if we have at least 2 components
            if len(formatted_value) >= 2:
                return {
                    "status": status,
                    "value": formatted_value
                }
    
    return {
        "status": "not_required",
        "value": None
    }


def format_comparison_table(table_data: Any) -> Optional[Dict[str, Any]]:
    """Format comparison table according to model structure."""
    if not table_data or not isinstance(table_data, dict):
        return None
    
    status = table_data.get("status", "not_required")
    if status not in ["required", "not_required"]:
        status = "not_required"
    
    value = None
    if status == "required" and table_data.get("value"):
        value = table_data["value"] if isinstance(table_data["value"], list) else None
    
    return {
        "status": status,
        "value": value
    }


def format_terminology_explainer(term_data: Any) -> Optional[Dict[str, Any]]:
    """Format terminology explainer according to model structure."""
    if not term_data or not isinstance(term_data, dict):
        return None
    
    status = term_data.get("status", "not_required")
    if status not in ["required", "not_required"]:
        status = "not_required"
    
    value = None
    if status == "required" and term_data.get("value"):
        value = term_data["value"] if isinstance(term_data["value"], list) else None
    
    return {
        "status": status,
        "value": value
    }


def format_analogies_metaphors(analogy_data: Any) -> Optional[Dict[str, Any]]:
    """Format analogies/metaphors according to model structure."""
    if not analogy_data or not isinstance(analogy_data, dict):
        return None
    
    status = analogy_data.get("status", "not_required")
    if status not in ["required", "not_required"]:
        status = "not_required"
    
    return {
        "status": status,
        "value": analogy_data.get("value") if status == "required" else None
    }


def format_customer_story(story_data: Any) -> Optional[Dict[str, Any]]:
    """Format customer story according to model structure."""
    if not story_data or not isinstance(story_data, dict):
        return None
    
    status = story_data.get("status", "not_required")
    if status not in ["required", "not_required"]:
        status = "not_required"
    
    return {
        "status": status,
        "value": story_data.get("value") if status == "required" else None
    }


def format_pricing_insight(pricing_data: Any) -> Optional[Dict[str, Any]]:
    """Format pricing insight according to model structure."""
    if not pricing_data or not isinstance(pricing_data, dict):
        return None
    
    status = pricing_data.get("status", "not_applicable")
    if status not in ["available", "not_applicable"]:
        status = "not_applicable"
    
    return {
        "status": status,
        "value": pricing_data.get("value") if status == "available" else None
    }


def ensure_statistics_dict(stats_data: Any) -> Dict[str, str]:
    """Ensure statistics is returned as a proper dictionary."""
    if isinstance(stats_data, dict):
        # Convert all values to strings
        return {str(k): str(v) for k, v in stats_data.items()}
    elif isinstance(stats_data, list):
        # Convert list to numbered dictionary
        return {f"metric_{i+1}": str(item) for i, item in enumerate(stats_data)}
    else:
        return {}


def calculate_confidence_score(result: Dict[str, Any], sources: List[Dict[str, Any]]) -> float:
    """Calculate confidence score based on response quality and source relevance."""
    confidence = 0.5  # Base confidence
    
    # Increase confidence based on number of sources
    if sources:
        confidence += min(len(sources) * 0.1, 0.3)
    
    # Increase confidence if structured fields are populated
    structured_fields = [
        result.get("star_response"),
        result.get("comparison_table"),
        result.get("terminology_explainer"),
        result.get("customer_story_snippet"),
        result.get("pricing_insight")
    ]
    
    populated_fields = sum(1 for field in structured_fields if field and field.get("status") == "required")
    confidence += populated_fields * 0.05
    
    # Increase confidence based on source similarity scores
    if sources:
        avg_similarity = sum(source.get("similarity_score", 0) for source in sources) / len(sources)
        confidence += avg_similarity * 0.2
    
    return min(confidence, 1.0)


def create_error_response(error_message: str, start_time: float) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "intent": "error",
        "question": None,
        "information_gap": f"Error occurred during analysis: {error_message}",
        "straightforward_answer": "I apologize, but I encountered an error while analyzing your request. Please try again.",
        "response": "I apologize, but I encountered an error while analyzing your request. Please try again.",
        "star_response": None,
        "comparison_table": None,
        "relevant_bullets": [],
        "statistics": {},
        "terminology_explainer": None,
        "analogies_or_metaphors": None,
        "customer_story_snippet": None,
        "pricing_insight": None,
        "escalation_flag": True,
        "follow_up_questions": [],
        "sentiment": "neutral",
        "salesPoints": [],
        "longform_response": "",
        "meta": {
            "error": error_message,
            "sources": [],
            "source_count": 0,
            "confidence": 0.0,
            "response_time_ms": int((time.time() - start_time) * 1000),
            "model_used": OPENAI_MODEL,
            "vector_search_enabled": False
        }
    }


def generate_comprehensive_star_response(query: str, sources: List[Dict], context: str) -> Dict[str, Any]:
    """
    Generate a comprehensive STAR format response using specialized prompting.
    This function creates detailed case studies with proper STAR structure.
    """
    from app.prompts import STAR_CASE_STUDY_PROMPT
    
    try:
        # Prepare context with source information
        source_context = "\n".join([
            f"Source: {source.get('file_name', 'Unknown')}\n{source.get('content', '')}"
            for source in sources[:5]  # Limit to top 5 sources
        ])
        
        # Create specialized prompt for STAR generation
        star_prompt = f"""
        {STAR_CASE_STUDY_PROMPT}
        
        USER QUERY: {query}
        
        CONTEXT SOURCES:
        {source_context}
        
        Generate a comprehensive STAR format case study based on the above information.
        """
        
        # This would use your AI client to generate the response
        # For now, return a structured template that can be filled
        return {
            "status": "required",
            "value": {
                "situation": "Detailed company background and business context from sources...",
                "task": "Specific challenges and problems that needed to be addressed...", 
                "action": "Comprehensive HealthAssist implementation details...",
                "result": "Quantified outcomes and measurable business impact..."
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating STAR response: {e}")
        return {
            "status": "not_required",
            "value": None
        }


def validate_star_response_quality(star_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and enhance STAR response quality based on provided examples.
    Ensures responses meet the comprehensive standards shown in the examples.
    """
    if not star_response or star_response.get("status") != "required":
        return star_response
    
    value = star_response.get("value")
    if not isinstance(value, dict):
        return star_response
    
    # Quality checks for each STAR component
    quality_criteria = {
        "situation": {
            "min_length": 150,
            "required_elements": ["company", "industry", "scale", "business context"]
        },
        "task": {
            "min_length": 150, 
            "required_elements": ["specific challenges", "quantified problems", "business impact"]
        },
        "action": {
            "min_length": 200,
            "required_elements": ["HealthAssist features", "integration", "implementation"]
        },
        "result": {
            "min_length": 150,
            "required_elements": ["metrics", "percentages", "quantified outcomes"]
        }
    }
    
    enhanced_value = {}
    for component, content in value.items():
        if component in quality_criteria:
            criteria = quality_criteria[component]
            
            # Ensure minimum length
            if len(str(content)) < criteria["min_length"]:
                # Add note about needing more detail
                enhanced_content = f"{content}\n\n[Note: Additional details needed for comprehensive case study]"
            else:
                enhanced_content = content
                
            enhanced_value[component] = enhanced_content
    
    return {
        "status": "required",
        "value": enhanced_value
    }
