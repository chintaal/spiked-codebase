"""
Test script to demonstrate the answer cache functionality with zero-latency responses.
"""

import asyncio
import httpx
import time
import json
from typing import List, Dict, Any

# API base URL
API_BASE_URL = "http://localhost:8000"

async def test_cache_functionality():
    """Test the answer cache functionality with various questions."""
    
    # Test questions - mix of exact matches and similar questions
    test_questions = [
        # Exact matches from cache
        "Can you provide a high-level overview of the HealthAssist architecture?",
        "What security measures are in place to ensure HIPAA compliance and data privacy?",
        "What EMR/EHR systems does HealthAssist seamlessly integrate with?",
        
        # Similar questions that should match cached answers
        "Tell me about HealthAssist's architecture",
        "How secure is HealthAssist for healthcare data?",
        "Which EHR systems can HealthAssist integrate with?",
        "What about HIPAA compliance and security?",
        "Can you explain the system architecture?",
        
        # Questions that might not be cached
        "What's the weather like today?",
        "How much does a hamburger cost?",
        "Tell me about your company's history"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 80)
        print("HEALTHASSIST ANSWER CACHE DEMONSTRATION")
        print("=" * 80)
        print()
        
        # First, check cache stats
        print("📊 CACHE STATISTICS")
        print("-" * 40)
        try:
            response = await client.get(f"{API_BASE_URL}/api/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"Total cached questions: {stats['cache_stats']['total_cached_questions']}")
                print(f"Cache file size: {stats['cache_stats']['cache_file_size']} bytes")
                print()
            else:
                print("Could not retrieve cache stats")
                print()
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            print()
        
        # Test each question
        for i, question in enumerate(test_questions, 1):
            print(f"🔍 TEST {i}: {question}")
            print("-" * 60)
            
            # Make request to analyze endpoint
            start_time = time.time()
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/analyze",
                    json={
                        "conversation": question,
                        "max_response_length": 200,
                        "tone": "professional",
                        "include_sources": True
                    }
                )
                
                elapsed_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check if this was a cache hit
                    cache_hit = result.get("meta", {}).get("cache_hit", False)
                    cache_similarity = result.get("meta", {}).get("cache_similarity", 0)
                    cached_question = result.get("meta", {}).get("cached_question", "")
                    
                    print(f"✅ Response Time: {elapsed_time * 1000:.2f}ms")
                    print(f"🎯 Cache Hit: {'YES' if cache_hit else 'NO'}")
                    
                    if cache_hit:
                        print(f"🔗 Similarity Score: {cache_similarity:.3f}")
                        print(f"📝 Matched Question: '{cached_question[:60]}...'")
                        print("⚡ ZERO-LATENCY RESPONSE!")
                    else:
                        print("🔄 Processed with full RAG pipeline")
                    
                    print(f"🤖 Intent: {result.get('intent', 'N/A')}")
                    print(f"💬 Response: {result.get('response', 'N/A')[:100]}...")
                    
                else:
                    print(f"❌ Error: HTTP {response.status_code}")
                    print(f"Details: {response.text}")
                
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
                elapsed_time = time.time() - start_time
                print(f"Time before error: {elapsed_time * 1000:.2f}ms")
            
            print()
        
        # Demonstrate performance comparison
        print("📈 PERFORMANCE COMPARISON")
        print("-" * 40)
        
        # Test cached question multiple times
        cached_question = "Can you provide a high-level overview of the HealthAssist architecture?"
        cache_times = []
        
        print(f"Testing cached question 5 times: '{cached_question[:50]}...'")
        
        for i in range(5):
            start_time = time.time()
            try:
                response = await client.post(
                    f"{API_BASE_URL}/analyze",
                    json={"conversation": cached_question}
                )
                elapsed_time = time.time() - start_time
                cache_times.append(elapsed_time * 1000)
                
                if response.status_code == 200:
                    result = response.json()
                    cache_hit = result.get("meta", {}).get("cache_hit", False)
                    print(f"  Run {i+1}: {elapsed_time * 1000:.2f}ms {'(CACHED)' if cache_hit else '(RAG)'}")
                
            except Exception as e:
                print(f"  Run {i+1}: Error - {e}")
        
        if cache_times:
            avg_cache_time = sum(cache_times) / len(cache_times)
            print(f"\n⚡ Average cached response time: {avg_cache_time:.2f}ms")
            print(f"🚀 Performance improvement: ~{(300 - avg_cache_time):.0f}ms faster than typical RAG")
        
        print()
        print("=" * 80)
        print("CACHE DEMONSTRATION COMPLETE")
        print("=" * 80)

async def initialize_cache():
    """Initialize the cache with preprocessed answers."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔄 Initializing answer cache...")
        try:
            response = await client.post(f"{API_BASE_URL}/api/cache/initialize")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result['message']}")
                stats = result.get('cache_stats', {})
                print(f"📊 Cached questions: {stats.get('total_cached_questions', 0)}")
            else:
                print(f"❌ Failed to initialize cache: {response.status_code}")
        except Exception as e:
            print(f"❌ Error initializing cache: {e}")

async def extend_cache():
    """Extend the cache with additional answers."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🔄 Extending answer cache...")
        try:
            response = await client.post(f"{API_BASE_URL}/api/cache/extend")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {result['message']}")
                stats = result.get('cache_stats', {})
                print(f"📊 Total cached questions: {stats.get('total_cached_questions', 0)}")
            else:
                print(f"❌ Failed to extend cache: {response.status_code}")
        except Exception as e:
            print(f"❌ Error extending cache: {e}")

async def main():
    """Main test function."""
    print("🚀 Starting HealthAssist Answer Cache Test")
    print()
    
    # Initialize cache first
    await initialize_cache()
    print()
    
    # Extend cache with additional answers
    await extend_cache()
    print()
    
    # Run cache functionality tests
    await test_cache_functionality()

if __name__ == "__main__":
    asyncio.run(main())
