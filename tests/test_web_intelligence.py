"""
Unit tests for the Web Intelligence Subsystem.
"""

import sys
from pathlib import Path
import pytest

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core_ai.integrations.web_intelligence import (
    get_web_intelligence,
    WebQueryClassifier,
    WebQueryMode,
    TieredTTLCache,
    SearchResult,
)


def test_classifier_browser_action():
    classifier = WebQueryClassifier()

    cases = [
        "Google pe search karo python tutorial",
        "Chrome me dhundo machine learning",
        "open google and search for latest AI news",
        "search on google for best laptops",
        "youtube pe search karo romantic songs",
    ]
    for text in cases:
        mode, q = classifier.classify(text)
        assert mode == WebQueryMode.BROWSER_ACTION, f"Failed on: {text} -> got {mode}"


def test_classifier_background_grounding():
    classifier = WebQueryClassifier()

    cases = [
        "Gold ka price kitna hai aaj?",
        "Aaj gold ka bhav kya hai",
        "What is the price of petrol today in Delhi?",
        "Bitcoin live rate",
        "Weather in Mumbai",
        "Aaj Delhi me mausam kaisa hai",
        "IPL match ka score kya hai",
        "Who is the current prime minister of UK?",
        "Latest news about OpenAI",
    ]
    for text in cases:
        mode, q = classifier.classify(text)
        assert mode == WebQueryMode.BACKGROUND_GROUNDING, f"Failed on: {text} -> got {mode}"


def test_classifier_direct_chat_exclusions():
    classifier = WebQueryClassifier()

    cases = [
        "Open notepad",
        "Kholo notepad",
        "Volume badhao thoda",
        "Write a python function to reverse a string",
        "Write a poem about rain",
        "Hello, how are you?",
        "Namaste, kya haal hai",
        "Calculate 15 * 24",
        "Remember that my birthday is tomorrow",
    ]
    for text in cases:
        mode, q = classifier.classify(text)
        assert mode == WebQueryMode.DIRECT_CHAT, f"Failed on: {text} -> got {mode}"


def test_classifier_deep_research():
    classifier = WebQueryClassifier()

    cases = [
        "Deep research on quantum computing",
        "Do detailed research about electric vehicles market",
        "Comprehensive analysis on renewable energy",
    ]
    for text in cases:
        mode, q = classifier.classify(text)
        assert mode == WebQueryMode.DEEP_RESEARCH, f"Failed on: {text} -> got {mode}"


def test_tiered_ttl_cache():
    cache = TieredTTLCache()
    dummy_res = [SearchResult(title="Test", url="https://example.com", snippet="Snippet")]

    cache.set("gold price", dummy_res, category="financial")
    hit = cache.get("gold price")
    assert hit is not None
    assert hit[0].title == "Test"

    # Normalize key test
    hit2 = cache.get("  GOLD   PRICE  ")
    assert hit2 is not None


def test_ground_prompt_flow():
    service = get_web_intelligence()

    # Direct chat query should return clean without web calls
    res = service.ground_prompt("Write a quick python hello world")
    assert res.mode == WebQueryMode.DIRECT_CHAT
    assert res.context_block == ""
    assert res.results == []

    # Grounding query should classify and return
    mode, _ = service.classify("Gold ka rate kya hai aaj")
    assert mode == WebQueryMode.BACKGROUND_GROUNDING


def test_tool_executor_web_search():
    from core_ai.core.tool_executor import web_search
    res = web_search("Gold price in India", max_results=2)
    assert res.get("success") is True
    assert "results" in res
    assert isinstance(res["results"], list)


def test_intent_executor_routing():
    from core_ai.core.intent_executor import IntentExecutor
    executor = IntentExecutor()

    # Background grounding intent should return grounded result without opening browser
    bg_res = executor.execute("search_web", {"query": "Gold ka price kitna hai aaj"})
    assert bg_res.get("success") is True
    assert bg_res.get("grounding_mode") == "background"
    assert len(bg_res.get("results", [])) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
