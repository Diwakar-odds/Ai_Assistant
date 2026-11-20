"""
Tests for Tri-Hybrid Web Intelligence Architecture [1 + 3 + 4].
Verifies:
1. SemanticVectorRouter (Strategy 1: Dense embedding cluster routing)
2. LlamaGrammar compilation (Strategy 3: BNF grammar constrained decoding)
3. NeuralMicroRouter (Strategy 4: Conversational Hinglish query reformulation)
"""

import pytest
from core_ai.integrations.web_intelligence.models import WebQueryMode
from core_ai.integrations.web_intelligence.semantic_router import SemanticVectorRouter
from core_ai.integrations.web_intelligence.grammar import get_search_router_grammar, get_boolean_grammar
from core_ai.integrations.web_intelligence.micro_router import NeuralMicroRouter


def test_semantic_router_modes():
    """Verify semantic vector router classifies queries into correct modes."""
    router = SemanticVectorRouter()

    # Sports query -> Background Grounding
    mode, score, _ = router.route("last india cricket match kiske sath tha")
    assert mode == WebQueryMode.BACKGROUND_GROUNDING
    assert score >= 0.55

    # System Date/Clock query -> Direct Chat (zero search latency)
    mode, score, _ = router.route("aaj date kya hai")
    assert mode == WebQueryMode.DIRECT_CHAT

    # Coding query -> Direct Chat
    mode, score, _ = router.route("write a python function to reverse a string")
    assert mode == WebQueryMode.DIRECT_CHAT


def test_bnf_grammar_compilation():
    """Verify native llama.cpp BNF grammars compile correctly."""
    router_grammar = get_search_router_grammar()
    assert router_grammar is not None

    bool_grammar = get_boolean_grammar()
    assert bool_grammar is not None


def test_micro_router_query_reformulation():
    """Verify micro-router cleans noisy conversational Hinglish into crisp search queries."""
    micro = NeuralMicroRouter()

    # Cricket query reformulation
    mode, clean_q = micro.route_and_reformulate("bhai last india cricket match kiske sath tha")
    assert mode == WebQueryMode.BACKGROUND_GROUNDING
    assert "india" in clean_q.lower()
    assert "cricket" in clean_q.lower()
    # Conversational stop words stripped
    assert "bhai" not in clean_q
    assert "kiske sath tha" not in clean_q

    # Gold price query reformulation
    mode, clean_q = micro.route_and_reformulate("bhai aaj sone ka bhav kitna chal raha hai market me")
    assert mode == WebQueryMode.BACKGROUND_GROUNDING
    assert "gold" in clean_q.lower()
    assert "price" in clean_q.lower()

    # Direct local queries preserved
    mode, clean_q = micro.route_and_reformulate("aaj date kya hai")
    assert mode == WebQueryMode.DIRECT_CHAT
