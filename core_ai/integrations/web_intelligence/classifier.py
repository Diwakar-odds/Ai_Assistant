"""
Deterministic Pre-LLM Web Query Classifier.
Operates in <1ms without any LLM call, ensuring compatibility with local GGUF
models and cloud models alike.
"""

import re
from typing import Tuple, Optional
from .models import WebQueryMode


class WebQueryClassifier:
    """Classifies user queries into 4 operational modes."""

    # =========================================================================
    # 1. BROWSER ACTION PATTERNS (Explicit User Desire for Visual Browser)
    # =========================================================================
    _BROWSER_EXPLICIT_PATTERNS = [
        # English: "open google and search ...", "search on chrome for ...", "browse to ..."
        r"^\s*(?:open|launch)\s+(?:google|chrome|edge|browser|firefox)\s+(?:and\s+)?(?:search|find|lookup)\s+(?:for\s+)?(?P<q>.+)",
        r"^\s*(?:search|lookup)\s+(?:on|in)\s+(?:google|chrome|edge|browser|firefox|youtube)\s+(?:for\s+)?(?P<q>.+)",
        r"^\s*google\s+(?:for\s+)?(?P<q>(?!chrome\b|maps\b|drive\b|docs\b|sheets\b|meet\b|photos\b|earth\b|calendar\b).+)",
        r"^\s*youtube\s+(?:pe\s+|par\s+)?(?:search\s+karo|chalao|play\s+karo)\s+(?P<q>.+)",

        # Hinglish: "google pe search karo...", "chrome me dhundo...", "browser me kholo..."
        r"^\s*(?:google|chrome|browser)\s+(?:pe|par|me|mein)\s+(?:search\s+karo|search\s+kar\s+do|dhundo|khojo|check\s+karo)\s+(?P<q>.+)",
        r"^\s*(?P<q>.+?)\s+(?:google|chrome|browser)\s+(?:pe|par|me|mein)\s+(?:search\s+karo|dhundo|khojo|khol\s+ke\s+dikhao)\s*$",
        r"^\s*(?:browser\s+me|browser\s+mein)\s+(?:kholo|search\s+karo|open\s+karo)\s+(?P<q>.+)",
        r"^\s*(?:dhundo|khojo)\s+(?:google\s+pe|internet\s+pe)\s+(?P<q>.+)",
    ]

    # =========================================================================
    # 2. DIRECT CHAT EXCLUSIONS (Do NOT Search The Web)
    # =========================================================================
    # System commands & App controls
    _SYSTEM_COMMAND_PATTERNS = [
        r"^\s*(?:open|launch|start|kholo|khol\s+do|chalao)\s+(?!google\b|chrome\b|edge\b|browser\b|website\b|web\b|internet\b)(?P<app>[a-zA-Z0-9_\-\s]+)$",
        r"^\s*(?:close|quit|exit|kill|band\s+karo|band\s+kro|bnd\s+karo|hatao)\s+(?P<app>.+)$",
        r"^\s*(?:volume|awaaz|awaz)\s+(?:up|down|mute|unmute|badhao|kam\s+karo|tez\s+karo|100|0|\d+)",
        r"^\s*(?:brightness|wifi|bluetooth|dark\s+mode|battery)\s+",
        r"^\s*(?:lock\s+screen|shutdown|restart|sleep\s+computer|turn\s+off\s+pc)",
    ]

    # Creative / Coding / Summarization / Reasoning
    _LOCAL_TASK_PATTERNS = [
        r"\b(?:write|code|create|generate|implement|debug|fix)\s+(?:a\s+)?(?:python|javascript|c\+\+|java|html|css|sql|function|script|class|algorithm|regex|code)\b",
        r"\b(?:python|js|cpp|java)\s+(?:ka\s+)?(?:code|function|program)\s+(?:likho|banao|dikhau)",
        r"\b(?:write|compose)\s+(?:a\s+)?(?:poem|story|essay|joke|song|email\s+draft|letter)\b",
        r"\b(?:kavita|kahani|joke|chutkula)\s+(?:sunao|batao|likho)",
        r"^\s*(?:calculate|solve|multiply|divide|add|subtract|\d+\s*[\+\-\*\/]\s*\d+)",
        r"^\s*(?:summarize|proofread|paraphrase|rewrite|translate)\s+(?:this|the\s+following|niche\s+likha)",
        r"^\s*(?:remember|yaad\s+rakho|save\s+to\s+memory|mera\s+naam\s+yaad)",
        r"^\s*(?:who\s+am\s+i|what\s+is\s+my\s+name|mera\s+naam\s+kya\s+hai)",
        # Date, Time, Calendar queries (Direct local clock facts)
        r"^\s*(?:what\s+is\s+today'?s?\s+date|aaj\s+date\s+kya\s+hai|aaj\s+ka\s+date|aaj\s+konsi\s+tarikh\s+hai|today'?s?\s+date|current\s+time|time\s+kya\s+hua|aaj\s+kya\s+din\s+hai|what\s+day\s+is\s+it|what\s+time\s+is\s+it|aaj\s+konsa\s+din\s+hai)\b",
    ]

    # Conversational / Greetings
    _GREETINGS = {
        "hi", "hello", "hey", "hola", "namaste", "pranam", "kya haal hai", "kaise ho",
        "how are you", "good morning", "good evening", "good night", "shubh ratri",
        "bye", "goodbye", "alvida", "see you", "thanks", "thank you", "shukriya", "dhanyawad",
        "who are you", "tum kaun ho", "aap kaun ho", "what can you do", "kya kar sakte ho"
    }

    # =========================================================================
    # 3. DEEP RESEARCH PATTERNS (Heavy Agentic Multi-Step Analysis)
    # =========================================================================
    _DEEP_RESEARCH_PATTERNS = [
        r"^\s*(?:do\s+|run\s+|perform\s+)?(?:deep\s+research|detailed\s+research|in-depth\s+research)\s+(?:on|about|for)\s+(?P<q>.+)",
        r"^\s*(?:comprehensive\s+analysis|market\s+research|detailed\s+report)\s+(?:on|about|for)\s+(?P<q>.+)",
        r"^\s*(?:research\s+karo|detailed\s+report\s+banao|pura\s+analysis\s+karo)\s+(?:on|about|pe\s+|par\s+)?(?P<q>.+)",
        r"^\s*(?:investigate|exhaustively\s+analyze)\s+(?P<q>.+)",
    ]

    # =========================================================================
    # 4. BACKGROUND GROUNDING SIGNALS (Live Real-Time / Factual Data)
    # =========================================================================
    # Perishable Commodities & Financials
    _FINANCIAL_COMMODITY_KEYWORDS = [
        "gold", "silver", "petrol", "diesel", "cng", "lpg", "crude oil",
        "bitcoin", "crypto", "ethereum", "solana", "btc", "eth",
        "dollar", "rupee", "usd", "inr", "eur", "forex", "exchange rate",
        "nifty", "sensex", "share market", "stock price", "nasdaq",
    ]

    _PRICE_VALUE_INDICATORS = [
        "price", "rate", "cost", "bhav", "daam", "kitna hai", "kya rate hai",
        "kya bhav hai", "aaj ka rate", "today price", "live price", "current rate"
    ]

    # Weather & Forecast
    _WEATHER_KEYWORDS = [
        "weather", "mausam", "temperature", "forecast", "rain", "barish",
        "aaj ka mausam", "humidity", "climate", "sunny", "aqi", "pollution"
    ]

    # Sports & Live Events
    _SPORTS_EVENT_KEYWORDS = [
        "score", "match", "cricket", "ipl", "football", "fifa", "world cup",
        "who won", "kaun jeeta", "points table", "live score", "medal tally"
    ]

    # Temporal / News Signals
    _RECENCY_NEWS_KEYWORDS = [
        "latest news", "taaza khabar", "breaking news", "today news", "aaj ki news",
        "current events", "trending", "kya chal raha hai", "kya hua aaj",
        "current prime minister", "current president", "who is currently",
        "recent developments", "new update", "released today", "launched recently"
    ]

    # General Factual Lookups (Entity / Question Indicators)
    _FACTUAL_TRIGGERS = [
        r"^(?:who is|who was|who are|kaun hai|koun hai)\s+(?P<q>[A-Z][a-zA-Z\s]+)",
        r"^(?:what is the capital of|population of|distance between|founder of|ceo of|net worth of)\s+(?P<q>.+)",
        r"\b(?:capital of|headquarters of|ceo of|founder of|net worth of)\b",
    ]

    def __init__(self):
        # Precompile regex for peak execution speed (<0.5ms)
        self._compiled_browser = [re.compile(p, re.IGNORECASE) for p in self._BROWSER_EXPLICIT_PATTERNS]
        self._compiled_system = [re.compile(p, re.IGNORECASE) for p in self._SYSTEM_COMMAND_PATTERNS]
        self._compiled_local = [re.compile(p, re.IGNORECASE) for p in self._LOCAL_TASK_PATTERNS]
        self._compiled_research = [re.compile(p, re.IGNORECASE) for p in self._DEEP_RESEARCH_PATTERNS]
        self._compiled_factual = [re.compile(p, re.IGNORECASE) for p in self._FACTUAL_TRIGGERS]

    def classify(self, message: str) -> Tuple[WebQueryMode, str]:
        """
        Classifies incoming user message into one of 4 modes.
        Returns: (WebQueryMode, extracted_search_query)
        """
        if not message or not message.strip():
            return WebQueryMode.DIRECT_CHAT, ""

        clean_msg = message.strip()
        lower_msg = clean_msg.lower()

        # ---------------------------------------------------------------------
        # STEP 1: Check BROWSER_ACTION (Explicit user desire to open browser UI)
        # ---------------------------------------------------------------------
        for pat in self._compiled_browser:
            m = pat.match(clean_msg)
            if m:
                query = m.groupdict().get("q", clean_msg).strip()
                return WebQueryMode.BROWSER_ACTION, query or clean_msg

        # ---------------------------------------------------------------------
        # STEP 2: Check DIRECT_CHAT Exclusions (Zero web search needed)
        # ---------------------------------------------------------------------
        # Exact greetings
        clean_punct = re.sub(r"[^\w\s]", "", lower_msg).strip()
        if clean_punct in self._GREETINGS:
            return WebQueryMode.DIRECT_CHAT, ""

        # System controls & app launches
        for pat in self._compiled_system:
            if pat.search(clean_msg):
                return WebQueryMode.DIRECT_CHAT, ""

        # Coding / creative / calculations / math
        for pat in self._compiled_local:
            if pat.search(clean_msg):
                return WebQueryMode.DIRECT_CHAT, ""

        # ---------------------------------------------------------------------
        # STEP 3: Check DEEP_RESEARCH (In-depth multi-query workflows)
        # ---------------------------------------------------------------------
        for pat in self._compiled_research:
            m = pat.match(clean_msg)
            if m:
                query = m.groupdict().get("q", clean_msg).strip()
                return WebQueryMode.DEEP_RESEARCH, query or clean_msg

        # ---------------------------------------------------------------------
        # STEP 4: Check BACKGROUND_GROUNDING (Real-time live grounding RAG)
        # ---------------------------------------------------------------------
        # 4a. Commodity / Financial Price Check (Gold, Petrol, Bitcoin, Stocks)
        has_commodity = any(c in lower_msg for c in self._FINANCIAL_COMMODITY_KEYWORDS)
        has_price_ind = any(p in lower_msg for p in self._PRICE_VALUE_INDICATORS)
        if has_commodity and (has_price_ind or any(w in lower_msg for w in ["aaj", "today", "current", "live", "rate", "price"])):
            return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # 4b. Weather & Temperature
        if any(w in lower_msg for w in self._WEATHER_KEYWORDS):
            return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # 4c. Sports & Live match results
        if any(s in lower_msg for s in self._SPORTS_EVENT_KEYWORDS):
            return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # 4d. News & Current Events
        if any(n in lower_msg for n in self._RECENCY_NEWS_KEYWORDS):
            return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # 4e. Factual questions with entity patterns
        for pat in self._compiled_factual:
            if pat.search(clean_msg):
                return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # 4f. General questions with recency triggers ("today", "aaj", "latest", "current")
        if any(w in lower_msg for w in ["today", "aaj", "current", "latest", "now", "abhi", "haal hi mein"]) and any(q in lower_msg for q in ["what", "kya", "who", "kaun", "where", "kahan", "when", "kab", "how", "kaise", "?"]):
            return WebQueryMode.BACKGROUND_GROUNDING, clean_msg

        # ---------------------------------------------------------------------
        # STEP 5: Default Fallback -> DIRECT_CHAT
        # ---------------------------------------------------------------------
        return WebQueryMode.DIRECT_CHAT, clean_msg
