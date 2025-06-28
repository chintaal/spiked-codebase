"""
Test script for Enhanced RAG functionality
"""

import asyncio
import json
import sys
import os

# Add the backend app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.enhanced_rag import enhanced_rag_analyze

async def test_enhanced_rag():
    """Test the enhanced RAG functionality with sample conversations."""
    
    test_conversations = [
        {
            "conversation": "Can you tell me about HealthAssist pricing and subscription models?",
            "expected_focus": "pricing, subscription, cost"
        },
        {
            "conversation": "How do I integrate HealthAssist with our existing systems? What APIs are available?",
            "expected_focus": "integration, API, technical implementation"
        },
        {
            "conversation": "What are the main features and capabilities of HealthAssist for healthcare organizations?",
            "expected_focus": "features, healthcare, capabilities"
        },
        {
            "conversation": "Can you provide examples of successful HealthAssist implementations and their ROI?",
            "expected_focus": "case studies, ROI, implementation success"
        },
        {
            "conversation": "What compliance and security features does HealthAssist offer for HIPAA and SOC 2?",
            "expected_focus": "compliance, security, HIPAA, SOC 2"
        }
    ]
    
    print("🚀 Testing Enhanced RAG Functionality\n")
    print("=" * 80)
    
    for i, test_case in enumerate(test_conversations, 1):
        print(f"\n📋 Test Case {i}: {test_case['expected_focus']}")
        print(f"Question: {test_case['conversation']}")
        print("-" * 60)
        
        try:
            # Call enhanced RAG analyze function
            result = await enhanced_rag_analyze(
                conversation=test_case['conversation'],
                max_response_length=500,
                tone="professional",
                include_sources=True
            )
            
            # Display key results
            print(f"✅ Intent: {result.get('intent', 'N/A')}")
            print(f"✅ Sources Found: {result.get('meta', {}).get('source_count', 0)}")
            print(f"✅ Confidence: {result.get('meta', {}).get('confidence', 0):.2f}")
            print(f"✅ Response Time: {result.get('meta', {}).get('response_time_ms', 0)}ms")
            
            # Check if enhanced fields are populated
            enhanced_fields = {
                "STAR Response": result.get('star_response'),
                "Comparison Table": result.get('comparison_table'),
                "Terminology Explainer": result.get('terminology_explainer'),
                "Customer Story": result.get('customer_story_snippet'),
                "Pricing Insight": result.get('pricing_insight')
            }
            
            print("\n📊 Enhanced Fields Status:")
            for field_name, field_data in enhanced_fields.items():
                if field_data and field_data.get('status') in ['required', 'available']:
                    print(f"   ✅ {field_name}: {field_data.get('status')}")
                else:
                    print(f"   ❌ {field_name}: not_required/not_applicable")
            
            # Show relevant bullets count
            bullets_count = len(result.get('relevant_bullets', []))
            print(f"\n📝 Relevant Bullets: {bullets_count}")
            
            # Show statistics count
            stats_count = len(result.get('statistics', {}))
            print(f"📈 Statistics: {stats_count}")
            
            # Show follow-up questions count
            followup_count = len(result.get('follow_up_questions', []))
            print(f"❓ Follow-up Questions: {followup_count}")
            
            # Display sample content
            print(f"\n💬 Straightforward Answer (preview):")
            answer = result.get('straightforward_answer', 'No answer generated')
            print(f"   {answer[:150]}{'...' if len(answer) > 150 else ''}")
            
            if result.get('relevant_bullets'):
                print(f"\n🔹 Sample Bullets:")
                for bullet in result.get('relevant_bullets', [])[:3]:
                    print(f"   • {bullet}")
            
            if result.get('statistics'):
                print(f"\n📊 Sample Statistics:")
                stats = result.get('statistics', {})
                for key, value in list(stats.items())[:3]:
                    print(f"   • {key}: {value}")
            
            print("\n" + "=" * 80)
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("=" * 80)
    
    print("\n🎉 Enhanced RAG Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_rag())
