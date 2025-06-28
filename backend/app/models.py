from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union


class TranscriptRequest(BaseModel):
    transcript: str


class SearchRequest(BaseModel):
    question: str


class StoreRequest(BaseModel):
    text: str


class TriggerRequest(BaseModel):
    trigger: str = "manual"


class ConversationAnalysisRequest(BaseModel):
    """Request model for analyzing a conversation snippet"""
    conversation: str
    max_response_length: Optional[int] = 500
    tone: Optional[str] = "professional"  # professional, friendly, assertive, etc.
    include_sources: Optional[bool] = True
    include_web_search: Optional[bool] = True  # Enable web search if internal sources are insufficient


class TermDefinition(BaseModel):
    """Definition of a technical or domain-specific term"""
    term: str
    definition: str


class ComparisonTableRow(BaseModel):
    """Row in a comparison table"""
    aspect: str
    option1: str
    option2: str


class StarResponseValue(BaseModel):
    """Structured STAR response content"""
    situation: Optional[str] = None
    task: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    summary: Optional[str] = None


class StarResponse(BaseModel):
    """STAR (Situation, Task, Action, Result) formatted response"""
    status: str  # "required" or "not_required"
    value: Optional[Union[str, StarResponseValue]] = None


class ComparisonTable(BaseModel):
    """Comparison table for contrasting options"""
    status: str  # "required" or "not_required" 
    value: Optional[List[ComparisonTableRow]] = None


class TerminologyExplainer(BaseModel):
    """Explanations of technical terms used in the response"""
    status: str  # "required" or "not_required"
    value: Optional[List[TermDefinition]] = None


class AnalogiesOrMetaphors(BaseModel):
    """Intuitive metaphors to explain complex concepts"""
    status: str  # "required" or "not_required"
    value: Optional[str] = None


class CustomerStorySnippet(BaseModel):
    """A brief customer story that illustrates the response"""
    status: str  # "required" or "not_required"
    value: Optional[str] = None


class PricingInsight(BaseModel):
    """Pricing-related information extracted from sources"""
    status: str  # "available" or "not_applicable"
    value: Optional[str] = None


class ConversationAnalysisResponse(BaseModel):
    """Enhanced response model for conversation analysis with RAG"""
    # Original fields
    intent: str
    question: Optional[str] = None
    information_gap: Optional[str] = None
    
    # Basic answer (always required)
    straightforward_answer: str
    
    # Enhanced fields (conditional)
    star_response: Optional[StarResponse] = None
    comparison_table: Optional[ComparisonTable] = None
    relevant_bullets: List[str] = []
    statistics: Dict[str, str] = {}
    terminology_explainer: Optional[TerminologyExplainer] = None
    analogies_or_metaphors: Optional[AnalogiesOrMetaphors] = None
    customer_story_snippet: Optional[CustomerStorySnippet] = None
    pricing_insight: Optional[PricingInsight] = None
    
    # Control fields
    escalation_flag: bool = False
    follow_up_questions: List[str] = []
    
    # Legacy fields for backward compatibility
    response: str  # Same as straightforward_answer
    sentiment: Optional[str] = None
    salesPoints: List[str] = []  # Will contain relevant_bullets
    
    # Metadata
    meta: Optional[Dict[str, Any]] = None
    longform_response: Optional[str] = None


class TranscriptionContext(BaseModel):
    """Context information for improving transcription formatting"""
    context: str = ""
    meeting_title: Optional[str] = None
    participants: Optional[List[str]] = None
    topics: Optional[List[str]] = None


class ActionItem(BaseModel):
    item: str
    context: str
    priority: Optional[str] = None


class ActionItemsResponse(BaseModel):
    action_items: List[ActionItem]
    meta: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    results: Optional[List[Dict[str, Any]]] = None
    answer: Optional[str] = None
    sources: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None


class StoreResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    error: Optional[str] = None


class SentimentRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    sentiment: str
    summary: Optional[str] = None
    positive_score: Optional[float] = None
    neutral_score: Optional[float] = None
    negative_score: Optional[float] = None
    mixed_score: Optional[float] = None
    success: Optional[bool] = True
    meta: Optional[Dict[str, Any]] = None


# Vexa API Models
class VexaMeetingRequest(BaseModel):
    """Request model for joining a meeting with Vexa bot"""
    native_meeting_id: str
    platform: str = "google_meet"
    language: Optional[str] = "en"
    bot_name: Optional[str] = "Spiked AI Bot"


class VexaMeetingResponse(BaseModel):
    """Response model for Vexa meeting bot operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    is_connection_error: Optional[bool] = None


class VexaTranscriptItem(BaseModel):
    """Model for a single transcript item from Vexa API"""
    id: str
    meeting_id: str
    text: str
    speaker: str
    timestamp: str
    confidence: Optional[float] = None


class VexaTranscriptResponse(BaseModel):
    """Response model for Vexa transcript retrieval"""
    success: bool
    data: Dict[str, Any] = None
    error: Optional[str] = None


class TranscriptionMessage(BaseModel):
    text: str
    is_final: bool = False