"""
BNF Grammars for Constrained Decoding (llama.cpp Native).
Guarantees mathematically that the local SLM / GGUF engine generates valid,
strictly typed JSON without syntax corruption, markdown tags, or hallucinated formatting.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# GBNF (GGML BNF) Grammar for strictly constrained JSON output:
# {"needs_search": true|false, "query": "..."}
SEARCH_ROUTER_GBNF = r'''
root ::= "{" ws "\"needs_search\":" ws boolean ws "," ws "\"query\":" ws string ws "}"
boolean ::= "true" | "false"
ws ::= [ \t\n]*
string ::= "\"" [^"\\]* "\""
'''

# GBNF Grammar for boolean classification: true | false
BOOLEAN_GBNF = r'''
root ::= "true" | "false"
'''


def get_search_router_grammar() -> Optional[object]:
    """
    Compiles and returns a LlamaGrammar object enforcing:
    {"needs_search": true|false, "query": "string"}
    """
    try:
        from llama_cpp import LlamaGrammar
        return LlamaGrammar.from_string(SEARCH_ROUTER_GBNF.strip())
    except ImportError:
        logger.debug("llama_cpp not available; grammar compilation skipped.")
        return None
    except Exception as e:
        logger.warning(f"Failed to compile SEARCH_ROUTER_GBNF: {e}")
        return None


def get_boolean_grammar() -> Optional[object]:
    """Compiles and returns a LlamaGrammar for true/false constrained decoding."""
    try:
        from llama_cpp import LlamaGrammar
        return LlamaGrammar.from_string(BOOLEAN_GBNF.strip())
    except ImportError:
        return None
    except Exception as e:
        logger.warning(f"Failed to compile BOOLEAN_GBNF: {e}")
        return None
