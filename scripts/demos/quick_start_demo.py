"""
Quick Start Demo
Demonstrates all new features in action

Run this to see everything working together!
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("🚀 ADVANCED FEATURES QUICK START DEMO")
print("=" * 80)
print()


async def demo_semantic_cache():
    """Demo semantic caching"""
    print("\n" + "=" * 80)
    print("1️⃣  SEMANTIC RESPONSE CACHE")
    print("=" * 80)
    
    try:
        from ai_assistant.ai.semantic_cache import get_response_cache
        
        cache = get_response_cache()
        
        # Cache a response
        print("\n📝 Caching: 'What is AI?' → 'Artificial Intelligence...'")
        cache.set("What is AI?", "Artificial Intelligence is...")
        
        # Try exact match
        print("\n🔍 Query: 'What is AI?'")
        result = cache.get("What is AI?")
        print(f"   Result: {result[:50]}... (EXACT MATCH)")
        
        # Try semantic match
        print("\n🔍 Query: 'Explain artificial intelligence'")
        result = cache.get("Explain artificial intelligence")
        if result:
            print(f"   Result: {result[:50]}... (SEMANTIC MATCH!)")
        else:
            print("   Result: Not found (similarity too low)")
        
        # Stats
        stats = cache.get_stats()
        print(f"\n📊 Cache Stats:")
        print(f"   Entries: {stats['cache_size_entries']}")
        print(f"   Hit rate: {stats['hit_rate_percent']}%")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_model_router():
    """Demo intelligent routing"""
    print("\n" + "=" * 80)
    print("2️⃣  INTELLIGENT MODEL ROUTER")
    print("=" * 80)
    
    try:
        from ai_assistant.ai.model_router import get_model_router
        
        router = get_model_router()
        
        test_queries = [
            ("What is 2+2?", "Simple calculation"),
            ("Write a Python sorting algorithm", "Coding task"),
            ("Explain quantum entanglement", "Complex reasoning"),
        ]
        
        for query, desc in test_queries:
            model, analysis = router.route(query)
            print(f"\n📝 Query: {query}")
            print(f"   Type: {desc}")
            print(f"   → Routed to: {model.name}")
            print(f"   → Tier: {model.tier.value}")
            print(f"   → Complexity: {analysis.complexity_score:.2f}")
            print(f"   → Cost: ${model.cost_per_1k_tokens}/1K tokens")
        
        # Stats
        stats = router.get_stats()
        print(f"\n💰 Cost Savings:")
        savings = stats['estimated_savings']
        print(f"   If all GPT-4: ${savings['if_all_gpt4_usd']:.2f}")
        print(f"   Actual cost: ${savings['actual_cost_usd']:.4f}")
        print(f"   Saved: ${savings['saved_usd']:.2f} ({savings['savings_percentage']:.0f}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_streaming():
    """Demo streaming responses"""
    print("\n" + "=" * 80)
    print("3️⃣  STREAMING RESPONSES")
    print("=" * 80)
    
    try:
        from ai_assistant.ai.streaming_handler import get_streaming_handler, StreamProvider
        
        handler = get_streaming_handler()
        
        print("\n📡 Streaming: 'Explain neural networks in one sentence'\n")
        print("Response: ", end='', flush=True)
        
        response = await handler.stream(
            provider=StreamProvider.GOOGLE,
            prompt="Explain neural networks in one sentence",
            model="gemini-2.0-flash-exp",
            on_chunk=lambda text: print(text, end='', flush=True),
            temperature=0.7,
            max_tokens=100
        )
        
        print("\n")
        print(f"\n✅ Streaming complete! Length: {len(response)} chars")
        
        # Stats
        stats = handler.get_stats()
        print(f"\n📊 Streaming Stats:")
        print(f"   Streams: {stats['total_streams']}")
        print(f"   Avg time: {stats['avg_time_ms']:.0f}ms")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   (This is normal if Google API key not configured)")


def demo_usage_analyzer():
    """Demo usage pattern analysis"""
    print("\n" + "=" * 80)
    print("4️⃣  USAGE PATTERN ANALYZER")
    print("=" * 80)
    
    try:
        from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
        
        analyzer = UsagePatternAnalyzer()
        
        print("\n📊 Analyzing usage patterns (last 30 days)...")
        results = analyzer.analyze_all(days_back=30)
        
        # Show results
        print(f"\n📈 Analysis Results:")
        
        if results['common_commands']:
            print(f"\n   Top Commands:")
            for cmd in results['common_commands'][:3]:
                print(f"   • {cmd['command_type']}: {cmd['count']} times ({cmd['percentage']:.1f}%)")
        
        time_p = results.get('time_patterns', {})
        if time_p:
            print(f"\n   Peak Usage:")
            print(f"   • {time_p.get('most_active_time', 'N/A')}")
        
        training_count = len(results.get('training_data', []))
        print(f"\n   Training Data:")
        print(f"   • {training_count} examples ready for fine-tuning")
        
        if training_count > 0:
            print("\n   💾 You can export training data with:")
            print("      analyzer.export_for_finetuning('data/training/finetune.jsonl')")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   (This is normal if no conversation history yet)")


def demo_emotion_detection():
    """Demo emotion detection"""
    print("\n" + "=" * 80)
    print("5️⃣  SPEECH EMOTION DETECTION")
    print("=" * 80)
    
    try:
        from ai_assistant.voice.emotion_detection import get_emotion_detector, Emotion
        
        detector = get_emotion_detector()
        
        print("\n🎭 Emotion-Based Response Adaptation:\n")
        
        emotions = [
            (Emotion.HAPPY, "User is happy"),
            (Emotion.FRUSTRATED, "User is frustrated"),
            (Emotion.SAD, "User is sad"),
        ]
        
        for emotion, desc in emotions:
            adaptation = detector.adapt_response_style(emotion)
            print(f"   {desc}:")
            print(f"   → Tone: {adaptation['tone']}")
            print(f"   → Strategy: {adaptation['suggestion']}")
            print()
        
        print("   💡 In real usage, this analyzes audio files automatically!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def demo_visual_verification():
    """Demo visual verification"""
    print("\n" + "=" * 80)
    print("6️⃣  VISUAL AUTOMATION VERIFICATION")
    print("=" * 80)
    
    try:
        from ai_assistant.automation.visual_verification import get_visual_verifier
        
        verifier = get_visual_verifier()
        
        print("\n👁️  Visual Verification Capabilities:\n")
        print("   ✅ Screenshot capture")
        print("   ✅ Before/after comparison")
        print("   ✅ Change detection")
        print("   ✅ Error dialog detection")
        print("   ✅ Confidence scoring")
        
        print("\n   💡 Example usage:")
        print("      before = verifier.capture_screenshot('before')")
        print("      # ... perform automation ...")
        print("      after = verifier.capture_screenshot('after')")
        print("      result = verifier.verify_action(before, after)")
        
        stats = verifier.get_success_rate()
        if stats['total_verifications'] > 0:
            print(f"\n📊 Verification Stats:")
            print(f"   Success rate: {stats['success_rate']}%")
            print(f"   Total verifications: {stats['total_verifications']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


async def demo_enhanced_integration():
    """Demo the integrated system"""
    print("\n" + "=" * 80)
    print("7️⃣  ENHANCED AI INTEGRATION (ALL FEATURES TOGETHER)")
    print("=" * 80)
    
    try:
        from ai_assistant.core.enhanced_integration import get_enhanced_ai
        
        ai = get_enhanced_ai()
        
        print("\n🚀 Processing query with ALL features enabled...\n")
        
        # Simple test query
        result = await ai.process_query(
            "What is machine learning?",
            enable_cache=True,
            enable_streaming=False  # Disable for demo
        )
        
        print(f"✅ Query processed successfully!")
        print(f"\n📊 Results:")
        print(f"   Model used: {result['model']}")
        print(f"   Time taken: {result['time_ms']:.0f}ms")
        print(f"   From cache: {result['cached']}")
        print(f"   Complexity: {result.get('complexity', 0):.2f}")
        
        # Get comprehensive stats
        stats = ai.get_stats()
        
        print(f"\n📈 Overall Stats:")
        print(f"   Total queries: {stats['enhanced_ai']['total_queries']}")
        
        if 'cache' in stats:
            print(f"   Cache hit rate: {stats['cache']['hit_rate_percent']}%")
        
        if 'routing' in stats:
            print(f"   Total cost: ${stats['routing']['total_cost_usd']:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   (This is normal if LLM APIs not configured)")


async def main():
    """Run all demos"""
    
    # Run demos
    await demo_semantic_cache()
    demo_model_router()
    await demo_streaming()
    demo_usage_analyzer()
    demo_emotion_detection()
    demo_visual_verification()
    await demo_enhanced_integration()
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print("\n📚 Next Steps:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Run activation: python scripts/activation/activate_advanced_features.py")
    print("   3. Read guide: docs/ADVANCED_FEATURES_GUIDE.md")
    print("   4. Integrate: from ai_assistant.core.enhanced_integration import get_enhanced_ai")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        print("   This is normal if dependencies aren't installed yet")
        print("   Run: pip install -r requirements.txt")
