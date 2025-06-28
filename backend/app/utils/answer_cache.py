"""
Answer Cache Manager for the /analyze endpoint.
Provides zero-latency responses for cached questions using batch-populated answers from the /analyze endpoint.
Implements true prompt caching by storing actual endpoint responses for canonical questions.
"""

import json
import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple, NamedTuple
from datetime import datetime
import difflib
import re
from pathlib import Path
import numpy as np
from dataclasses import dataclass, asdict
from collections import defaultdict

import openai
from app.config import OPENAI_API_KEY

# Setup logging
logger = logging.getLogger(__name__)

# Configure OpenAI for embedding generation
client = openai.OpenAI(api_key=OPENAI_API_KEY)

@dataclass
class CachedAnswer:
    """Structured representation of a cached answer."""
    intent: str
    question: str
    information_gap: str
    straightforward_answer: str
    response: str
    sentiment: str
    star_response: Dict[str, str]
    comparison_table: List[Dict[str, str]]
    relevant_bullets: List[str]
    statistics: Dict[str, Any]
    terminology_explainer: str
    analogies_or_metaphors: str
    customer_story_snippet: str
    pricing_insight: str
    escalation_flag: bool
    follow_up_questions: List[str]
    longform_response: str
    salesPoints: List[str]
    meta: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

class EmbeddingIndex:
    """Efficient embedding-based index for fast similarity search."""
    
    def __init__(self):
        self.embeddings: np.ndarray = np.array([])
        self.question_hashes: List[str] = []
        self.question_texts: List[str] = []
        self.is_built = False
    
    def add_embedding(self, question: str, embedding: List[float]):
        """Add an embedding to the index."""
        question_hash = hashlib.sha256(question.encode()).hexdigest()[:16]
        
        if len(self.embeddings) == 0:
            self.embeddings = np.array([embedding])
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])
        
        self.question_hashes.append(question_hash)
        self.question_texts.append(question)
        self.is_built = True
    
    def build_index(self, questions_embeddings: Dict[str, List[float]]):
        """Build index from existing questions and embeddings."""
        embeddings_list = []
        self.question_hashes = []
        self.question_texts = []
        
        for question, embedding in questions_embeddings.items():
            if embedding:  # Only add if embedding exists
                embeddings_list.append(embedding)
                question_hash = hashlib.sha256(question.encode()).hexdigest()[:16]
                self.question_hashes.append(question_hash)
                self.question_texts.append(question)
        
        if embeddings_list:
            self.embeddings = np.array(embeddings_list)
            self.is_built = True
    
    def find_similar(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar questions using vectorized operations."""
        if not self.is_built or len(self.embeddings) == 0:
            return []
        
        query_vec = np.array(query_embedding)
        
        # Compute cosine similarity with all embeddings at once
        similarities = np.dot(self.embeddings, query_vec) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vec)
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return question texts and similarities
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.5:  # Only return reasonable matches
                results.append((self.question_texts[idx], float(similarities[idx])))
        
        return results

class AnswerCache:
    """
    Manages cached answers for batch prompt caching with semantic similarity matching.
    Cache is populated by calling the /analyze endpoint for canonical questions and storing the actual responses.
    Provides zero-latency responses for questions similar to those in the cache.
    """
    
    def __init__(self, cache_file_path: str = None):
        if cache_file_path is None:
            # Use a path relative to the project root
            backend_dir = Path(__file__).parent.parent.parent
            cache_file_path = backend_dir / "app" / "uploads" / "cache_documents" / "answer_cache.json"
        
        self.cache_file_path = Path(cache_file_path)
        self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self.question_cache: Dict[str, Dict[str, Any]] = {}
        self.question_embeddings: Dict[str, List[float]] = {}
        
        # Initialize embedding index for fast similarity search
        self.embedding_index = EmbeddingIndex()
        
        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Load existing cache
        self.load_cache()
    
    def load_cache(self):
        """Load cache from disk."""
        try:
            if self.cache_file_path.exists():
                with open(self.cache_file_path, 'r') as f:
                    data = json.load(f)
                    self.question_cache = data.get('questions', {})
                    self.question_embeddings = data.get('embeddings', {})
                    
                # Build embedding index for fast similarity search
                if self.question_embeddings:
                    self.embedding_index.build_index(self.question_embeddings)
                    logger.info(f"Built embedding index with {len(self.question_embeddings)} embeddings")
                    
                logger.info(f"Loaded {len(self.question_cache)} cached answers")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.question_cache = {}
            self.question_embeddings = {}
            self.embedding_index = EmbeddingIndex()
    
    def save_cache(self):
        """Save cache to disk."""
        try:
            data = {
                'questions': self.question_cache,
                'embeddings': self.question_embeddings,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.cache_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.question_cache)} cached answers")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI API."""
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return []
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using embeddings."""
        try:
            embedding1 = self.get_embedding(text1)
            embedding2 = self.get_embedding(text2)
            
            if not embedding1 or not embedding2:
                return 0.0
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def normalize_question(self, text: str) -> str:
        """Normalize question text for better matching."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove punctuation but keep important words
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common question words that don't add meaning
        stop_words = {'can', 'you', 'please', 'tell', 'me', 'about', 'what', 'how', 'is', 'are', 'the', 'a', 'an'}
        words = text.split()
        meaningful_words = [w for w in words if w not in stop_words or len(w) > 3]
        
        return ' '.join(meaningful_words)

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using difflib for fast approximate matching."""
        # Normalize both texts
        norm_text1 = self.normalize_question(text1)
        norm_text2 = self.normalize_question(text2)
        
        # Use difflib for quick similarity calculation
        similarity = difflib.SequenceMatcher(None, norm_text1, norm_text2).ratio()
        
        # Also check for key word overlap
        words1 = set(norm_text1.split())
        words2 = set(norm_text2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return similarity
        
        # Calculate Jaccard similarity for word overlap
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        jaccard_similarity = intersection / union if union > 0 else 0
        
        # Combine both similarities with emphasis on sequence matching
        combined_similarity = (similarity * 0.7) + (jaccard_similarity * 0.3)
        
        return combined_similarity
    
    def find_similar_question(self, query: str, threshold: float = 0.7) -> Tuple[Optional[str], float]:
        """Find the most similar cached question with optimized performance."""
        best_match = None
        best_score = 0.0
        
        # Normalize the query for better matching
        normalized_query = self.normalize_question(query)
        logger.debug(f"Searching for match to normalized query: '{normalized_query}'")
        
        # STEP 1: Try exact text match first (fastest)
        for cached_question in self.question_cache.keys():
            if query.lower().strip() == cached_question.lower().strip():
                logger.info(f"Found exact match: '{cached_question[:50]}...'")
                return cached_question, 1.0
        
        # STEP 2: Try fast text-based similarity
        text_matches = []
        for cached_question in self.question_cache.keys():
            text_similarity = self.calculate_text_similarity(query, cached_question)
            
            if text_similarity > 0.4:  # Only consider reasonable matches
                text_matches.append((cached_question, text_similarity))
                logger.debug(f"Text similarity with '{cached_question[:50]}...': {text_similarity:.3f}")
        
        # Sort by similarity and get the best text match
        text_matches.sort(key=lambda x: x[1], reverse=True)
        
        if text_matches and text_matches[0][1] >= threshold:
            best_match, best_score = text_matches[0]
            logger.info(f"Found text-based match: '{best_match[:50]}...' with similarity {best_score:.3f}")
            
            # Additional validation: check if key terms match
            if self._validate_match(query, best_match):
                return best_match, best_score
            else:
                logger.warning(f"Text match failed validation, trying semantic matching")
        
        # STEP 3: Use pre-built embedding index for semantic similarity (no API calls)
        if self.embedding_index.is_built:
            logger.debug("Using pre-built embedding index for semantic search")
            query_embedding = self.get_embedding(query)  # Only one API call for the query
            if query_embedding:
                similar_questions = self.embedding_index.find_similar(query_embedding, top_k=5)
                
                for question, similarity in similar_questions:
                    if similarity >= threshold and self._validate_match(query, question):
                        logger.info(f"Found semantic match: '{question[:50]}...' with similarity {similarity:.3f}")
                        return question, similarity
        
        logger.info("No suitable match found above threshold")
        return None, 0.0
    
    def _validate_match(self, query: str, cached_question: str) -> bool:
        """Validate that the match makes sense by checking key terms."""
        # Extract key terms from both questions
        query_terms = set(self.normalize_question(query).split())
        cached_terms = set(self.normalize_question(cached_question).split())
        
        # Important terms that should match for healthcare questions
        important_terms = {
            'architecture', 'security', 'hipaa', 'compliance', 'emr', 'ehr', 'integration', 
            'multilingual', 'language', 'scalability', 'performance', 'licensing', 'pricing',
            'database', 'api', 'fhir', 'backup', 'disaster', 'recovery', 'nlp', 'few', 'shot',
            'ontology', 'medical', 'citibank', 'pfizer', 'client', 'customer', 'healthassist',
            'kore', 'bot', 'conversational', 'ai', 'analytics', 'deployment', 'configuration'
        }
        
        # Check if any important terms are present in both
        query_important = query_terms.intersection(important_terms)
        cached_important = cached_terms.intersection(important_terms)
        
        # If both have important terms, they should overlap significantly
        if query_important and cached_important:
            overlap = query_important.intersection(cached_important)
            overlap_ratio = len(overlap) / len(query_important.union(cached_important))
            
            logger.debug(f"Important terms - Query: {query_important}, Cached: {cached_important}, Overlap: {overlap}, Ratio: {overlap_ratio:.3f}")
            
            # Require at least 40% overlap of important terms (slightly more lenient)
            return overlap_ratio >= 0.4
        
        # If no important terms, check general term overlap
        general_overlap = len(query_terms.intersection(cached_terms))
        total_terms = len(query_terms.union(cached_terms))
        
        if total_terms > 0:
            general_ratio = general_overlap / total_terms
            # For general questions, require at least 30% term overlap
            return general_ratio >= 0.3
        
        # If no terms at all, reject the match
        return False
    
    def get_cached_answer(self, query: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """Get cached answer for a query if similar question exists."""
        start_time = time.time()
        
        # Try to find similar question
        similar_question, similarity_score = self.find_similar_question(query, threshold)
        
        if similar_question:
            cached_answer = self.question_cache[similar_question].copy()
            
            # Update metadata
            cached_answer["meta"]["cache_hit"] = True
            cached_answer["meta"]["cache_similarity"] = similarity_score
            cached_answer["meta"]["cached_question"] = similar_question
            cached_answer["meta"]["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # Track cache hit
            self._cache_hits += 1
            
            logger.info(f"Cache hit for query: '{query[:50]}...' -> '{similar_question[:50]}...' (similarity: {similarity_score:.3f})")
            return cached_answer
        
        # Track cache miss
        self._cache_misses += 1
        logger.info(f"No cache hit for query: '{query[:50]}...'")
        return None
    
    def add_to_cache(self, question: str, answer: Dict[str, Any]):
        """Add a new question-answer pair to the cache."""
        # Store the answer
        self.question_cache[question] = answer
        
        # Generate and store embedding
        embedding = self.get_embedding(question)
        self.question_embeddings[question] = embedding
        
        # Add to embedding index for fast similarity search
        if embedding:
            self.embedding_index.add_embedding(question, embedding)
        
        # Save to disk
        self.save_cache()        
        logger.info(f"Added new answer to cache: '{question[:50]}...'")
        
    def clear_cache(self):
        """Clear all cached answers."""
        self.question_cache = {}
        self.question_embeddings = {}
        self.embedding_index = EmbeddingIndex()
        self._cache_hits = 0
        self._cache_misses = 0
        if self.cache_file_path.exists():
            self.cache_file_path.unlink()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_cached_questions": len(self.question_cache),
            "cache_file_size": self.cache_file_path.stat().st_size if self.cache_file_path.exists() else 0,
            "last_updated": datetime.fromtimestamp(self.cache_file_path.stat().st_mtime).isoformat() if self.cache_file_path.exists() else None
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        stats = {
            "total_entries": len(self.question_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percentage": round(hit_rate, 2),
            "last_updated": datetime.fromtimestamp(self.cache_file_path.stat().st_mtime).isoformat() if self.cache_file_path.exists() else None,
            "avg_response_time": 0.05,  # Cache responses are very fast (50ms)
            "total_savings": self._cache_hits * 2.5,  # Assume 2.5s saved per hit
            "embedding_index_built": self.embedding_index.is_built,
            "embeddings_count": len(self.question_embeddings)
        }
        return stats

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all cache entries for management interface."""
        entries = []
        for question, answer_data in self.question_cache.items():
            entry = {
                "id": hashlib.md5(question.encode()).hexdigest(),
                "question": question,
                "answer": answer_data.get("straightforward_answer", ""),
                "confidence": answer_data.get("meta", {}).get("confidence", 1.0),
                "created_at": answer_data.get("meta", {}).get("timestamp", ""),
                "intent": answer_data.get("intent", ""),
                "sentiment": answer_data.get("sentiment", "neutral")
            }
            entries.append(entry)
        return entries

    def update_entry(self, entry_id: str, question: str, answer: str, confidence: float = None) -> bool:
        """Update a specific cache entry."""
        # Find the entry by ID
        for cached_question, answer_data in self.question_cache.items():
            current_id = hashlib.md5(cached_question.encode()).hexdigest()
            if current_id == entry_id:
                # Remove old entry
                del self.question_cache[cached_question]
                if cached_question in self.question_embeddings:
                    del self.question_embeddings[cached_question]
                
                # Add updated entry
                updated_data = answer_data.copy()
                updated_data["straightforward_answer"] = answer
                if confidence is not None:
                    updated_data.setdefault("meta", {})["confidence"] = confidence
                
                self.question_cache[question] = updated_data
                
                # Update embeddings
                try:
                    embedding = self.get_embedding(question)
                    self.question_embeddings[question] = embedding
                    self.embedding_index.add_embedding(question, embedding)
                except Exception as e:
                    logger.error(f"Error updating embedding for question: {str(e)}")
                
                self.save_cache()
                return True
        return False

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a specific cache entry."""
        for cached_question, answer_data in list(self.question_cache.items()):
            current_id = hashlib.md5(cached_question.encode()).hexdigest()
            if current_id == entry_id:
                del self.question_cache[cached_question]
                if cached_question in self.question_embeddings:
                    del self.question_embeddings[cached_question]
                self.save_cache()
                return True
        return False

    def optimize_cache(self, max_entries: int = 1000, min_confidence: float = 0.5) -> int:
        """Optimize cache by removing old or low-confidence entries."""
        removed_count = 0
        entries_to_remove = []
        
        # Sort entries by confidence and recency
        entries = []
        for question, answer_data in self.question_cache.items():
            confidence = answer_data.get("meta", {}).get("confidence", 1.0)
            timestamp = answer_data.get("meta", {}).get("timestamp", "")
            entries.append((question, confidence, timestamp))
        
        # Remove low confidence entries
        for question, confidence, timestamp in entries:
            if confidence < min_confidence:
                entries_to_remove.append(question)
        
        # If still too many entries, remove oldest ones
        if len(self.question_cache) - len(entries_to_remove) > max_entries:
            # Sort by timestamp (oldest first)
            remaining_entries = [(q, c, t) for q, c, t in entries if q not in entries_to_remove]
            remaining_entries.sort(key=lambda x: x[2])  # Sort by timestamp
            
            excess_count = len(remaining_entries) - max_entries
            for i in range(excess_count):
                entries_to_remove.append(remaining_entries[i][0])
        
        # Remove selected entries
        for question in entries_to_remove:
            if question in self.question_cache:
                del self.question_cache[question]
                removed_count += 1
            if question in self.question_embeddings:
                del self.question_embeddings[question]
        
        if removed_count > 0:
            self.save_cache()
            logger.info(f"Cache optimized: removed {removed_count} entries")
        
        return removed_count

    def update_config(self, max_entries: int = None, confidence_threshold: float = None, 
                     similarity_threshold: float = None) -> Dict[str, Any]:
        """Update cache configuration."""
        config = getattr(self, '_config', {})
        
        if max_entries is not None:
            config['max_entries'] = max_entries
        if confidence_threshold is not None:
            config['confidence_threshold'] = confidence_threshold
        if similarity_threshold is not None:
            config['similarity_threshold'] = similarity_threshold
            
        self._config = config
        return config

    def get_config(self) -> Dict[str, Any]:
        """Get current cache configuration."""
        return getattr(self, '_config', {
            'max_entries': 1000,
            'confidence_threshold': 0.7,
            'similarity_threshold': 0.8
        })

    def store_answer(self, question: str, answer_data: Dict[str, Any]):
        """Store a complete answer structure in the cache."""
        # Ensure proper metadata structure
        if "meta" not in answer_data:
            answer_data["meta"] = {}
        
        answer_data["meta"]["timestamp"] = datetime.now().isoformat()
        answer_data["meta"]["source"] = "api_response"
        
        # Store the complete answer data
        self.add_to_cache(question, answer_data)
        logger.info(f"Stored answer for question: '{question[:50]}...'")

    def store_simple_answer(self, question: str, answer: str, confidence: float = 1.0):
        """Store a simple answer string in the cache (legacy method)."""
        answer_data = {
            "intent": "user_question",
            "question": question,
            "information_gap": "",
            "straightforward_answer": answer,
            "response": answer,
            "sentiment": "neutral",
            "star_response": {},
            "comparison_table": [],
            "relevant_bullets": [],
            "statistics": {},
            "terminology_explainer": "",
            "analogies_or_metaphors": "",
            "customer_story_snippet": "",
            "pricing_insight": "",
            "escalation_flag": False,
            "follow_up_questions": [],
            "longform_response": answer,
            "salesPoints": [],
            "meta": {
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "source": "manual_entry"
            }
        }
        
        self.add_to_cache(question, answer_data)

    def search_similar(self, query: str, limit: int = 10, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar questions in the cache."""
        try:
            query_embedding = self.get_embedding(query)
            similar_questions = self.embedding_index.find_similar(query_embedding, top_k=limit)
            
            results = []
            for question, similarity in similar_questions:
                if similarity >= threshold and question in self.question_cache:
                    answer_data = self.question_cache[question]
                    results.append({
                        "question": question,
                        "answer": answer_data.get("straightforward_answer", ""),
                        "similarity": similarity,
                        "confidence": answer_data.get("meta", {}).get("confidence", 1.0)
                    })
            
            return results
        except Exception as e:
            logger.error(f"Error searching cache: {str(e)}")
            return []

    def create_backup(self) -> str:
        """Create a backup of the current cache."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.cache_file_path.parent}/answer_cache_backup_{timestamp}.json"
        
        backup_data = {
            "question_cache": self.question_cache,
            "question_embeddings": self.question_embeddings,
            "backup_timestamp": timestamp,
            "original_file": str(self.cache_file_path)
        }
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Cache backup created: {backup_path}")
        return backup_path

    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore cache from a backup file."""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                backup_path = self.cache_file_path.parent / backup_file
                if not backup_path.exists():
                    return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            self.question_cache = backup_data.get("question_cache", {})
            self.question_embeddings = backup_data.get("question_embeddings", {})
            
            # Rebuild embedding index
            if self.question_embeddings:
                self.embedding_index.build_index(self.question_embeddings)
            
            self.save_cache()
            logger.info(f"Cache restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring cache from backup: {str(e)}")
            return False

    def analyze_query_similarity(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Analyze query similarity against all cached questions for debugging."""
        results = []
        
        # Get text-based similarities
        for cached_question in self.question_cache.keys():
            text_sim = self.calculate_text_similarity(query, cached_question)
            
            # Get semantic similarity if embeddings available
            semantic_sim = 0.0
            if cached_question in self.question_embeddings:
                query_embedding = self.get_embedding(query)
                if query_embedding:
                    cached_embedding = self.question_embeddings[cached_question]
                    if cached_embedding:
                        # Calculate cosine similarity
                        dot_product = sum(a * b for a, b in zip(query_embedding, cached_embedding))
                        magnitude1 = sum(a * a for a in query_embedding) ** 0.5
                        magnitude2 = sum(b * b for b in cached_embedding) ** 0.5
                        
                        if magnitude1 > 0 and magnitude2 > 0:
                            semantic_sim = dot_product / (magnitude1 * magnitude2)
            
            # Check validation
            validation_passed = self._validate_match(query, cached_question)
            
            results.append({
                "cached_question": cached_question[:100] + "..." if len(cached_question) > 100 else cached_question,
                "text_similarity": round(text_sim, 3),
                "semantic_similarity": round(semantic_sim, 3),
                "validation_passed": validation_passed,
                "combined_score": round(max(text_sim, semantic_sim), 3),
                "would_match_at_70": max(text_sim, semantic_sim) >= 0.7 and validation_passed,
                "would_match_at_65": max(text_sim, semantic_sim) >= 0.65 and validation_passed
            })
        
        # Sort by combined score
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return results[:top_k]

# Global cache instance
answer_cache = AnswerCache()
