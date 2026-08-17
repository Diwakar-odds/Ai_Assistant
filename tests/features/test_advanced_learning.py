"""
Quick Start Example for Advanced Learning Systems
Run this to test all learning modules
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_feedback_learning():
    """Test RLHF-inspired feedback learning"""
    print("=" * 60)
    print("1. Testing Advanced Feedback Learning System")
    print("=" * 60)
    
    from ai_assistant.ai.advanced_feedback_learning import AdaptiveLearningEngine
    
    engine = AdaptiveLearningEngine()
    
    # Simulate positive feedback
    engine.collect_feedback(
        response_id="test_001",
        feedback_type="thumbs_up",
        response_text="Here's a detailed explanation with examples...",
        context={"task": "explanation", "detail_level": "high"}
    )
    
    # Simulate negative feedback
    engine.collect_feedback(
        response_id="test_002",
        feedback_type="thumbs_down",
        response_text="ok",
        context={"task": "explanation", "detail_level": "low"}
    )
    
    # Test preference pair
    engine.collect_preference_pair(
        prompt="Explain Python decorators",
        chosen_response="A decorator is a function that modifies another function. Here's an example: @cache def slow_function()...",
        rejected_response="Use @ symbol"
    )
    
    # Get statistics
    stats = engine.get_learning_stats()
    print(f"\n✅ Feedback collected: {stats['total_feedback']}")
    print(f"✅ Preference pairs: {stats['preference_pairs']}")
    print(f"✅ Average reward: {stats['average_reward']:.2f}")
    print(f"✅ Learning thread active: {engine.learning_thread.is_alive()}")
    
    return True

def test_intent_classification():
    """Test intent classification with NER"""
    print("\n" + "=" * 60)
    print("2. Testing Intent Classification & NER")
    print("=" * 60)
    
    from ai_assistant.ai.intent_classification import IntentClassifier
    
    classifier = IntentClassifier()
    
    test_cases = [
        "Open Chrome and search for Python tutorials",
        "What's the weather like today?",
        "Write a function to calculate fibonacci numbers",
        "Hey, how are you doing?",
        "Send an email to john@example.com about the meeting tomorrow"
    ]
    
    for text in test_cases:
        intent, confidence, entities = classifier.classify_intent(text, {})
        print(f"\n📝 Text: {text}")
        print(f"   Intent: {intent} ({confidence:.2%})")
        if entities:
            print(f"   Entities: {entities}")
    
    # Test learning from correction
    classifier.correct_intent(
        user_input="Open Chrome",
        predicted_intent="open_application",
        correct_intent="automation",
        confidence=0.5
    )
    print(f"\n✅ Learned from user correction")
    
    return True

def test_adaptive_prompts():
    """Test adaptive prompt optimization"""
    print("\n" + "=" * 60)
    print("3. Testing Adaptive Prompt Engineering")
    print("=" * 60)
    
    from ai_assistant.ai.adaptive_prompts import PromptOptimizer
    
    optimizer = PromptOptimizer()
    
    # Get best template for coding
    template = optimizer.get_best_template('coding')
    if template:
        print(f"\n✅ Best coding template: {template.name}")
        print(f"   Success rate: {template.success_rate:.2%}")
        print(f"   Usage count: {template.usage_count}")
        
        # Render with example
        prompt = optimizer.render_prompt(
            template.id,
            code="def greet(name):\n    return f'Hello, {name}!'",
        )
        print(f"\n📄 Rendered prompt preview:")
        print(prompt[:200] + "...")
        
        # Simulate feedback
        optimizer.record_feedback(template.id, 0.95, "Excellent explanation!")
        print(f"\n✅ Feedback recorded")
    
    # Get insights
    insights = optimizer.get_optimization_insights()
    print(f"\n📊 Insights:")
    print(f"   Total templates: {insights['total_templates']}")
    print(f"   Templates by category: {dict(insights['templates_by_category'])}")
    
    return True

def test_multimodal_learning():
    """Test multi-modal learning"""
    print("\n" + "=" * 60)
    print("4. Testing Multi-Modal Learning Integration")
    print("=" * 60)
    
    from ai_assistant.ai.multimodal_learning import MultiModalLearningEngine
    
    engine = MultiModalLearningEngine()
    
    # Simulate interaction with voice and text
    voice_data = {
        'pitch': 150.0,
        'energy': 0.8,
        'tempo': 120.0,
        'speaking_rate': 4.5
    }
    
    text_data = {
        'preference': 'detailed',
        'formality': 0.7,
        'length': 150
    }
    
    # Record several interactions
    emotions = ['happy', 'neutral', 'happy', 'excited']
    for i, emotion in enumerate(emotions):
        engine.record_interaction(
            user_id="test_user",
            voice_data=voice_data,
            text_data=text_data,
            emotion=emotion,
            context=f"interaction_{i}",
            quality=0.8 + i * 0.05
        )
    
    print(f"\n✅ Recorded {len(emotions)} interactions")
    
    # Predict user state
    state = engine.predict_user_state("test_user", voice_data)
    print(f"\n🎯 Predicted user state:")
    print(f"   Emotion: {state['emotion']}")
    print(f"   Text preference: {state['text_preference']}")
    print(f"   Engagement level: {state['engagement_level']:.2%}")
    
    # Get insights
    insights = engine.get_contextual_insights("test_user")
    print(f"\n📊 User insights:")
    print(f"   Primary emotion: {insights['primary_emotion']}")
    print(f"   Interaction frequency: {insights['interaction_frequency']:.2f}/day")
    
    return True

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 ADVANCED LEARNING SYSTEMS - QUICK START")
    print("=" * 60)
    
    results = {}
    
    # Test each module
    try:
        results['feedback_learning'] = test_feedback_learning()
    except Exception as e:
        print(f"❌ Feedback learning failed: {e}")
        results['feedback_learning'] = False
    
    try:
        results['intent_classification'] = test_intent_classification()
    except Exception as e:
        print(f"❌ Intent classification failed: {e}")
        results['intent_classification'] = False
    
    try:
        results['adaptive_prompts'] = test_adaptive_prompts()
    except Exception as e:
        print(f"❌ Adaptive prompts failed: {e}")
        results['adaptive_prompts'] = False
    
    try:
        results['multimodal_learning'] = test_multimodal_learning()
    except Exception as e:
        print(f"❌ Multimodal learning failed: {e}")
        results['multimodal_learning'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    for module, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {module}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n🎯 Overall: {passed}/{total} modules working")
    
    if passed == total:
        print("\n🎉 All learning systems operational!")
        print("\n📚 Next steps:")
        print("   1. Integrate with conversational AI (see docs/ADVANCED_LEARNING_SYSTEMS.md)")
        print("   2. Add feedback UI to web interface")
        print("   3. Monitor learning progress in data/*.db files")
        print("   4. Review insights using get_*_insights() methods")
    else:
        print("\n⚠️  Some systems failed. Check error messages above.")
        print("   - Ensure dependencies installed: pip install sentence-transformers scikit-learn")
        print("   - Check database permissions in data/ folder")
        print("   - Review logs for detailed errors")

if __name__ == "__main__":
    main()
