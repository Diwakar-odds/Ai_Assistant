import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    entities: Dict[str, Any]
    confidence: float

class IntentExtractor:
    """
    A simple rule-based intent and entity extractor for natural language commands.
    Uses regex patterns to identify intents and extract entities.
    """
    
    def __init__(self):
        # Define intent patterns and associated entities
        self.patterns = {
            # Research and summarize intent
            r"research (.+?) and give me a summary": {
                "intent": "research_summarize",
                "entities": ["topic"]
            },
            r"research (.+?)$": {
                "intent": "research",
                "entities": ["topic"]
            },
            # Scrape and summarize intent with optional time
            r"scrape (.+?) at (\d{1,2}:\d{2}) and give me a summary": {
                "intent": "scrape_summarize_scheduled",
                "entities": ["url", "time"]
            },
            r"scrape (.+?) and give me a summary": {
                "intent": "scrape_summarize",
                "entities": ["url"]
            },
            r"scrape (.+?)$": {
                "intent": "scrape",
                "entities": ["url"]
            },
            # Create file intent
            r"create a? file named? (.+?) with content (.+)": {
                "intent": "create_file",
                "entities": ["filename", "content"]
            },
            r"create file (.+?)$": {
                "intent": "create_file",
                "entities": ["filename"]
            },
            # General web search
            r"search (?:for )?(.+?)$": {
                "intent": "web_search",
                "entities": ["query"]
            },
            # Summarize text
            r"summarize (.+?)$": {
                "intent": "summarize_text",
                "entities": ["text"]
            },
            # Notify intent
            r"notify me (.+?)$": {
                "intent": "notify",
                "entities": ["message"]
            }
        }
        # Compile regex patterns
        self.compiled = []
        for pattern, info in self.patterns.items():
            self.compiled.append((re.compile(pattern, re.IGNORECASE), info))
    
    def extract(self, text: str) -> IntentResult:
        """
        Extract intent and entities from the given text.
        Returns an IntentResult with the best match.
        """
        text = text.strip()
        best_match = None
        best_confidence = 0.0
        
        for pattern_regex, info in self.compiled:
            match = pattern_regex.match(text)
            if match:
                # Calculate confidence based on match groups
                groups = match.groups()
                # Simple confidence: if we have non-empty groups, higher confidence
                non_empty = sum(1 for g in groups if g is not None and g.strip() != "")
                total_groups = len(groups)
                confidence = non_empty / total_groups if total_groups > 0 else 0.5
                # Boost confidence if we matched the whole string
                if match.group(0) == text:
                    confidence = min(1.0, confidence + 0.3)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (info, groups)
        
        if best_match is None:
            # Fallback: try to extract a generic intent
            return IntentResult(
                intent="unknown",
                entities={"raw_text": text},
                confidence=0.0
            )
        
        info, groups = best_match
        entities = {}
        entity_names = info["entities"]
        for i, name in enumerate(entity_names):
            if i < len(groups):
                entities[name] = groups[i].strip() if groups[i] is not None else None
        
        return IntentResult(
            intent=info["intent"],
            entities=entities,
            confidence=best_confidence
        )