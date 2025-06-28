"""
Example usage of the Smart Sales Assistant API
"""
import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Set your API base URL here
API_BASE_URL = "http://localhost:8000"  # Change this to your actual API URL

async def analyze_conversation(
    client: httpx.AsyncClient,
    conversation: str,
    max_response_length: int = 200,
    tone: str = "professional",
    include_sources: bool = False
) -> Dict[str, Any]:
    """
    
    Call the /analyze endpoint to analyze a conversation snippet
    
    Args:
        client: HTTP client
        conversation: Conversation snippet to analyze
        max_response_length: Maximum length of response in words
        tone: Tone for the response (professional, friendly, assertive)
        include_sources: Whether to include knowledge sources in the response
        
    Returns:
        API response as dictionary
    """
    url = f"{API_BASE_URL}/analyze"
    
    # Prepare the request payload
    payload = {
        "conversation": conversation,
        "max_response_length": max_response_length,
        "tone": tone,
        "include_sources": include_sources
    }
    
    try:
        # Make the API call
        start_time = time.time()
        response = await client.post(url, json=payload)
        response.raise_for_status()
        end_time = time.time()
        
        # Parse response
        result = response.json()
        
        # Add response time
        result["meta"] = result.get("meta", {})
        result["meta"]["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        
        return result
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return {"error": f"HTTP error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        print(f"Error calling API: {str(e)}")
        return {"error": str(e)}

async def main():
    """Run example API calls"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 80)
        print("Smart Sales Assistant API Demo")
        print("=" * 80)
        
        # Example 1: Basic pricing question
        print("\nExample 1: Customer asking about pricing")
        print("-" * 50)
        
        conversation1 = "I'm interested in your product but I'm worried about the pricing. Is there a discount for yearly subscriptions?"
        
        result1 = await analyze_conversation(
            client,
            conversation1,
            max_response_length=150,
            tone="professional"
        )
        
        if "error" not in result1:
            print(f"Intent: {result1['intent']}")
            print(f"Question: {result1['question']}")
            print(f"Information Gap: {result1['information_gap']}")
            print(f"Sentiment: {result1['sentiment']}")
            print(f"Response Time: {result1['meta']['response_time_ms']} ms")
            print("\nSuggested Response:")
            print(f"\"{result1['response']}\"")
        else:
            print(f"Error: {result1.get('error', 'Unknown error')}")
        
        # Example 2: Technical question with sources
        print("\nExample 2: Customer asking about compliance with sources")
        print("-" * 50)
        
        conversation2 = "I'm concerned about HIPAA compliance and patient data security. How does your system protect sensitive information?"
        
        result2 = await analyze_conversation(
            client,
            conversation2,
            max_response_length=200,
            tone="professional",
            include_sources=True
        )
        
        if "error" not in result2:
            print(f"Intent: {result2['intent']}")
            print(f"Question: {result2['question']}")
            print(f"Information Gap: {result2['information_gap']}")
            print(f"Sentiment: {result2['sentiment']}")
            print(f"Response Time: {result2['meta']['response_time_ms']} ms")
            print("\nSuggested Response:")
            print(f"\"{result2['response']}\"")
            
            if result2.get('meta', {}).get('sources'):
                print("\nSources:")
                for i, source in enumerate(result2['meta']['sources'], 1):
                    print(f"{i}. {source[:100]}..." if len(source) > 100 else f"{i}. {source}")
        else:
            print(f"Error: {result2.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())

async def analyze_conversation(conversation: str, max_length: int = 100, tone: str = "professional") -> Dict[str, Any]:
    """
    Send a conversation snippet to the analyze endpoint.
    
    Args:
        conversation: The conversation snippet to analyze
        max_length: Maximum length of the generated response
        tone: Tone of the response (professional, friendly, assertive)
        
    Returns:
        The analysis result as a dictionary
    """
    url = f"{API_BASE_URL}/analyze"
    
    # Prepare the request data
    data = {
        "conversation": conversation,
        "max_response_length": max_length,
        "tone": tone,
        "include_sources": True
    }
    
    # Send the request
    async with httpx.AsyncClient() as client:
        try:
            start_time = time.time()
            response = await client.post(url, json=data, timeout=10.0)
            elapsed_time = time.time() - start_time
            
            # Handle non-200 responses
            if response.status_code != 200:
                return {
                    "error": f"API returned status code {response.status_code}",
                    "detail": response.text
                }
            
            # Parse the JSON response
            result = response.json()
            
            # Add performance metrics
            result["_meta"] = {
                "latency_ms": round(elapsed_time * 1000, 2)
            }
            
            return result
        except Exception as e:
            return {
                "error": "Exception occurred",
                "detail": str(e)
            }

async def run_examples():
    """Run several example conversations through the API"""
    examples = [
        "I'm interested in your product but I'm not sure if it's compatible with our EHR system.",
        "The pricing seems a bit high compared to your competitors.",
        "How quickly can we implement this solution? We need it urgently.",
        "I like the features, but my team is concerned about HIPAA compliance.",
        "I'm worried about the training required for our staff to use this system."
    ]
    
    print("Smart Sales Assistant API Example Usage\n")
    
    for i, example in enumerate(examples, 1):
        print(f"Example {i}: \"{example}\"")
        result = await analyze_conversation(example)
        
        if "error" in result:
            print(f"Error: {result['error']}\n{result.get('detail', '')}\n")
            continue
        
        # Format and print the results
        print(f"Intent: {result['intent']}")
        print(f"Question: {result.get('question', 'None')}")
        print(f"Information Gap: {result['information_gap']}")
        print(f"Sentiment: {result['sentiment']}")
        print(f"Suggested Response: \"{result['response']}\"")
        print(f"Latency: {result.get('_meta', {}).get('latency_ms', 'N/A')}ms")
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_examples())
