"""
Multi-Step Command Parser
Breaks down complex commands into sequential, parallel, or conditional sub-tasks.
Handles English, Hindi, Hinglish, mixed delimiters, quoted text protection,
variable passing ({prev.output}), and specialized multi-agent intent mapping.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """Represents a single step in a task chain."""
    step: int
    intent: str
    params: Dict[str, Any]
    dependencies: List[int] = None
    original_text: str = ""

    # Rich orchestration metadata (backward-compatible optional defaults)
    step_id: str = ""
    description: str = ""
    execution_target: str = "local"          # local | agent | hybrid
    agent_id: Optional[str] = None
    capability: Optional[str] = None
    parallel_group: Optional[str] = None
    condition: Optional[str] = None          # None | always | on_success | on_failure
    on_failure: str = "abort"                # abort | continue | fallback | skip
    fallback_step: Optional[int] = None
    output_key: Optional[str] = None
    requires_confirmation: bool = False

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if not self.step_id:
            self.step_id = f"step_{self.step}"
        if not self.description:
            self.description = self.original_text or self.intent
        if not self.output_key:
            self.output_key = self.step_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "step_id": self.step_id,
            "intent": self.intent,
            "description": self.description,
            "params": dict(self.params or {}),
            "dependencies": list(self.dependencies or []),
            "original_text": self.original_text,
            "execution_target": self.execution_target,
            "agent_id": self.agent_id,
            "capability": self.capability,
            "parallel_group": self.parallel_group,
            "condition": self.condition,
            "on_failure": self.on_failure,
            "fallback_step": self.fallback_step,
            "output_key": self.output_key,
            "requires_confirmation": self.requires_confirmation,
        }


# Action hints used to distinguish multi-step command clauses from noun enumerations
_ACTION_HINT_WORDS = {
    # English OS / Web / Media / File / Wait
    "open", "launch", "start", "run", "close", "quit", "exit", "kill", "stop",
    "search", "google", "lookup", "browse", "navigate", "visit", "check", "inspect",
    "play", "pause", "resume", "skip", "forward", "mute", "unmute", "increase", "decrease",
    "raise", "lower", "set", "turn", "switch", "toggle", "enable", "disable",
    "type", "write", "save", "copy", "paste", "move", "delete", "remove", "rename",
    "find", "locate", "send", "msg", "message", "text", "reply", "forward",
    "create", "make", "generate", "build", "convert", "edit", "format",
    "wait", "sleep", "delay", "say", "speak", "announce", "notify",
    "lock", "shutdown", "restart", "download", "upload", "screenshot", "scan",
    # Agent capability verbs
    "research", "investigate", "scrape", "wikipedia", "summarize", "summarise",
    "draft", "compose", "proofread", "rewrite", "translate", "analyze", "analyse",
    "plot", "visualize", "chart", "query", "optimize", "email", "schedule", "book",
    "organize", "clean", "declutter", "backup", "transcribe", "synthesize", "draw",
    "design", "render", "fill", "monitor", "flashcards", "quiz",
    # Hinglish
    "kholo", "khol", "kholna", "chalu", "chalao", "band", "hatao", "karo", "kar",
    "bhejo", "likho", "bajao", "lagao", "suno", "dhundo", "khojo", "banao", "bana",
    "dikhao", "batao", "badhao", "kam", "ruko", "thehro",
    # Hindi Devanagari
    "खोलो", "खोल", "खोलिए", "खोलना", "चालू", "चलाओ", "बंद", "हटाओ", "करो",
    "भेजो", "लिखो", "बजाओ", "लगाओ", "सुनो", "ढूंढो", "खोजो", "बनाओ", "दिखाओ",
    "बताओ", "बढ़ाओ", "कम", "रुको", "ठहरो", "सर्च", "प्ले", "म्यूट", "अनम्यूट",
}

_STRONG_SPLIT_SYNTAX_RE = re.compile(r'(&&|\|\||->|=>|;|\r?\n)')

_PARALLEL_CONNECTORS = [
    "at the same time", "in parallel", "simultaneously", "concurrently",
    "meanwhile", "alongside", "ek saath", "saath mein", "ek sath", "sath mein",
    "एक साथ", "साथ में",
]

_FALLBACK_CONNECTORS = [
    "if it fails then", "if that fails then", "if it fails", "if that fails",
    "otherwise", "fallback", "warna", "agar fail ho", "नहीं तो", "वरना", "else",
]

_SEQUENTIAL_STRONG_CONNECTORS = [
    "and then", "after that", "followed by", "aur phir", "aur fir",
    "uske baad", "iske baad", "फिर से", "और फिर", "उसके बाद", "इसके बाद",
    "के बाद", "बाद में", "afterwards", "then", "and next", "next up", "phir", "fir",
    "फिर", "तथा", "एवं",
]

_AMBIGUOUS_CONNECTORS = [
    "and also", "also", "aur", "और", "and",
]

_CONTEXT_PREV_OUTPUT_RE = re.compile(
    r'\b(?:it|this|that|the\s+(?:result|output|research|summary|findings|content|report))\b',
    re.IGNORECASE,
)


class MultiStepCommandParser:
    """
    Parses complex, multi-step commands into structured TaskStep chains
    with sequential, parallel, conditional, and specialized agent metadata.
    """

    def __init__(self):
        """Initialize parser with patterns and shared IntentRouter."""
        self.sequential_keywords = [
            'फिर', 'phir', 'then', 'fir',
            'और फिर', 'aur phir', 'aur fir', 'and then',
            'के बाद', 'ke baad', 'uske baad', 'iske baad', 'after that', 'followed by',
            'फिर से', 'phir se', 'again',
            'बाद में', 'baad me', 'later', 'and next', 'next up', 'afterwards',
            'तथा', 'एवं', 'और', 'aur', 'and',
        ]
        self.parallel_keywords = list(_PARALLEL_CONNECTORS)
        self.fallback_keywords = list(_FALLBACK_CONNECTORS)

        # Fallback regex patterns (Unicode / Devanagari matra-safe: [^\s,]+)
        self.action_patterns = {
            'open_app': [
                r'([^\s,]+)\s+(?:खोलो|kholo|open|start|चालू\s*करो|launch)\b',
                r'(?:खोलो|kholo|open)\s+([^\s,]+)',
            ],
            'send_message': [
                r'([^\s,]+)\s+को\s+(?:message|भेजो|send|बोल\s*दो)\b',
                r'(?:message|भेजो|send)\s+(?:to\s+)?([^\s,]+)',
            ],
            'type_text': [
                r'(?:type|लिखो|likho)\s+(.+)',
                r'(.+)\s+(?:लिखो|likho)\s*$',
            ],
            'play_video': [
                r'(?:video|वीडियो)\s+(?:play|चलाओ|chalao)',
                r'(?:play|चलाओ)\s+(?:video|वीडियो)',
            ],
            'skip_time': [
                r'(\d+)\s+(?:minutes?|mins?|मिनट)\s+(?:skip|आगे\s*बढ़ाओ|forward)',
                r'(?:skip|आगे\s*बढ़ाओ)\s+(\d+)\s+(?:minutes?|mins?|मिनट)',
            ],
        }

        try:
            from ai_assistant.ai.intent_router import IntentRouter
            self.intent_router = IntentRouter()
        except Exception as e:
            self.intent_router = None
            logger.warning(f"Intent router not available in multi_step_parser: {e}")

    # =========================================================================
    # QUOTE / URL / PATH PROTECTION LEXER
    # =========================================================================

    @staticmethod
    def _protect_spans(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace quoted strings, URLs, Windows/Unix paths, placeholders ({prev.output}),
        and formatted numbers (1,000) with temporary sentinel tokens so splitters
        never slice inside them.
        """
        mapping: Dict[str, str] = {}
        counter = 0

        def _store(match: re.Match) -> str:
            nonlocal counter
            token = f"__PTOKEN_{counter}__"
            counter += 1
            mapping[token] = match.group(0)
            return token

        # Order matters: quotes -> brace placeholders -> URLs -> Windows paths -> comma numbers
        protected = text
        patterns = [
            r'"[^"]*"',
            r"'[^']*'",
            r'`[^`]*`',
            r'\{[A-Za-z0-9_.\-]+\}',
            r'https?://[^\s,;]+',
            r'[A-Za-z]:\\[^\s,;]+',
            r'\b\d{1,3}(?:,\d{3})+\b',
        ]
        combined = re.compile("|".join(f"(?:{p})" for p in patterns))
        protected = combined.sub(_store, protected)
        return protected, mapping

    @staticmethod
    def _restore_spans(text: str, mapping: Dict[str, str]) -> str:
        if not text or not mapping:
            return text
        out = text
        # Multi-pass in case tokens were nested (though single regex avoids nesting)
        for token, original in mapping.items():
            out = out.replace(token, original)
        return out

    # =========================================================================
    # MULTI-STEP DETECTION & SPLITTING
    # =========================================================================

    def _clause_looks_actionable(self, raw_clause: str) -> bool:
        """Return True if a clause looks like an executable command/task rather than a plain noun."""
        text = raw_clause.strip()
        if not text:
            return False

        # Never treat single punctuation or pure number as actionable
        if re.fullmatch(r'[\d\W]+', text):
            return False

        # Pure greeting prefix ("Hello", "Hi Pulsar") is not a standalone command step
        if re.fullmatch(r'(?:hi|hello|hey|namaste|ok|okay|theek|please|pls|plz)(?:\s+pulsar)?[!.,?]*', text, re.IGNORECASE):
            return False

        # Check normalized/raw tokens for known action verbs
        try:
            from ai_assistant.core.local_command_normalizer import (
                normalize_hinglish_devanagari,
                strip_punctuation_unicode,
            )
            norm = normalize_hinglish_devanagari(text)
            tokens = strip_punctuation_unicode(norm).lower().split()
            raw_tokens = strip_punctuation_unicode(text).lower().split()
        except Exception:
            tokens = re.findall(r'[\w\u0900-\u097F]+', text.lower())
            raw_tokens = tokens

        if any(t in _ACTION_HINT_WORDS for t in tokens) or any(t in _ACTION_HINT_WORDS for t in raw_tokens):
            return True

        # Check IntentRouter Tier 1 directly
        if getattr(self, 'intent_router', None):
            try:
                res = self.intent_router._fast_match(text)
                if res and res.intent_name and res.intent_name not in ('conversational', 'info_query'):
                    return True
            except Exception:
                pass

        return False

    def split_with_relations(self, command: str) -> List[Dict[str, str]]:
        """
        Split a command into segments while preserving connector relationship semantics
        ('start', 'sequential', 'parallel', 'conditional_fallback') and protecting quoted spans.
        """
        if not command or not command.strip():
            return []

        raw = command.strip()

        # 0. Check multi-line numbered or bulleted task lists:
        # e.g. "1. open chrome\n2. search python\n3. wait 2 seconds"
        lines = [ln.strip() for ln in re.split(r'\r?\n', raw) if ln.strip()]
        if len(lines) >= 2 and all(re.match(r'^(?:\d+[\.\)]|[-*•])\s+.+', ln) for ln in lines):
            segments = []
            for idx, ln in enumerate(lines):
                body = re.sub(r'^(?:\d+[\.\)]|[-*•])\s+', '', ln).strip()
                if body:
                    segments.append({
                        "text": body,
                        "relation": "start" if idx == 0 else "sequential",
                        "delimiter": "\n",
                        "explicit": True,
                    })
            if len(segments) >= 2:
                return segments

        # Also handle inline numbered lists ("1. open chrome 2. search python")
        inline_nums = re.split(r'(?:^|\s+)(?:\d+[\.\)])\s+', raw)
        inline_parts = [p.strip(" ,;") for p in inline_nums if p.strip(" ,;")]
        if len(inline_parts) >= 2 and re.match(r'^\s*1[\.\)]\s+', raw):
            return [
                {
                    "text": part,
                    "relation": "start" if idx == 0 else "sequential",
                    "delimiter": "num",
                    "explicit": True,
                }
                for idx, part in enumerate(inline_parts)
            ]

        # 1. Protect quotes, URLs, file paths, placeholders, numbers
        protected, token_map = self._protect_spans(raw)

        # 2. Build unified tokenizer for delimiters
        par_alts = "|".join(re.escape(k) for k in sorted(_PARALLEL_CONNECTORS, key=len, reverse=True))
        fb_alts = "|".join(re.escape(k) for k in sorted(_FALLBACK_CONNECTORS, key=len, reverse=True))
        seq_alts = "|".join(re.escape(k) for k in sorted(_SEQUENTIAL_STRONG_CONNECTORS, key=len, reverse=True))
        amb_alts = "|".join(re.escape(k) for k in sorted(_AMBIGUOUS_CONNECTORS, key=len, reverse=True))

        # Connector regex captures:
        # - optional comma/space + parallel keyword
        # - symbolic || / && / -> / => / ; / newline
        # - optional comma/space + fallback keyword
        # - optional comma/space + strong sequential keyword
        # - comma optionally followed by ambiguous keyword ("and"/"aur")
        # - standalone ambiguous keyword surrounded by spaces/boundaries
        delim_pattern = re.compile(
            rf'''
            (?P<sym_parallel>&&)
            |(?P<sym_fallback>\|\|)
            |(?P<sym_seq>->|=>|;|\r?\n)
            |(?P<par>(?:,\s*|\s+)(?:{par_alts})(?!\S))
            |(?P<fb>(?:,\s*|\s+)(?:{fb_alts})(?!\S))
            |(?P<seq_kw>(?:,\s*|\s+)(?:{seq_alts})(?!\S))
            |(?P<comma_amb>\s*,\s*(?:(?:{amb_alts})(?!\S))?)
            |(?P<amb>\s+(?:{amb_alts})(?=\s+))
            ''',
            re.IGNORECASE | re.UNICODE | re.VERBOSE
        )

        # Find all delimiter spans left-to-right
        matches = list(delim_pattern.finditer(protected))
        if not matches:
            return [{
                "text": self._restore_spans(protected, token_map).strip(),
                "relation": "start",
                "delimiter": "",
                "explicit": False,
            }]

        raw_chunks: List[Dict[str, Any]] = []
        cursor = 0
        next_rel = "start"
        next_delim = ""
        next_explicit = False

        for m in matches:
            part = protected[cursor:m.start()].strip()
            if part or not raw_chunks:
                raw_chunks.append({
                    "text": part,
                    "relation": next_rel,
                    "delimiter": m.group(0),  # delimiter BEFORE next chunk; stored below
                    "prev_delimiter": next_delim,
                    "explicit": next_explicit,
                })

            if m.group("sym_parallel") or m.group("par"):
                # Also strip trailing leading 'and' / 'aur' before "at the same time" / "simultaneously"
                if raw_chunks and re.search(r'\s+(?:and|aur|और)\s*$', raw_chunks[-1]["text"], re.IGNORECASE):
                    raw_chunks[-1]["text"] = re.sub(
                        r'\s+(?:and|aur|और)\s*$', '', raw_chunks[-1]["text"], flags=re.IGNORECASE
                    ).strip()
                next_rel = "parallel"
                next_explicit = True
            elif m.group("sym_fallback") or m.group("fb"):
                if raw_chunks and re.search(r'\s+(?:or)\s*$', raw_chunks[-1]["text"], re.IGNORECASE):
                    raw_chunks[-1]["text"] = re.sub(
                        r'\s+(?:or)\s*$', '', raw_chunks[-1]["text"], flags=re.IGNORECASE
                    ).strip()
                next_rel = "conditional_fallback"
                next_explicit = True
            elif m.group("sym_seq") or m.group("seq_kw"):
                next_rel = "sequential"
                next_explicit = True
            else:
                # comma_amb or amb
                next_rel = "sequential"
                next_explicit = False

            next_delim = m.group(0)
            cursor = m.end()

        tail = protected[cursor:].strip()
        if tail:
            raw_chunks.append({
                "text": tail,
                "relation": next_rel,
                "prev_delimiter": next_delim,
                "explicit": next_explicit,
            })

        # Filter empty chunks while preserving ordering
        raw_chunks = [c for c in raw_chunks if c.get("text", "").strip()]
        if not raw_chunks:
            return []

        # Restore protected tokens and apply smart merge for ambiguous commas / 'and' / 'aur'
        restored_chunks: List[Dict[str, Any]] = []
        for idx, ch in enumerate(raw_chunks):
            txt = self._restore_spans(ch["text"], token_map).strip()
            if not txt:
                continue
            item = {
                "text": txt,
                "relation": ch["relation"] if idx > 0 else "start",
                "prev_delimiter": ch.get("prev_delimiter", ""),
                "explicit": bool(ch.get("explicit", False)),
            }
            restored_chunks.append(item)

        # Smart merge pass: only keep ambiguous splits when BOTH sides are actionable
        # or explicit syntax/connector demanded the split.
        merged: List[Dict[str, str]] = []
        for idx, item in enumerate(restored_chunks):
            if idx == 0 or not merged:
                merged.append({
                    "text": item["text"],
                    "relation": "start",
                    "delimiter": item["prev_delimiter"],
                    "explicit": item["explicit"],
                })
                continue

            if item["explicit"]:
                # Explicit delimiter (&&, ;, ->, then, phir, simultaneously, otherwise)
                # Still avoid splitting pure Q&A if neither side is actionable unless syntax is &&/; /->
                prev_txt = merged[-1]["text"]
                if (
                    _STRONG_SPLIT_SYNTAX_RE.search(item["prev_delimiter"])
                    or self._clause_looks_actionable(prev_txt)
                    or self._clause_looks_actionable(item["text"])
                ):
                    merged.append({
                        "text": item["text"],
                        "relation": item["relation"],
                        "delimiter": item["prev_delimiter"],
                        "explicit": True,
                    })
                    continue

            # Ambiguous split (',', 'and', 'aur', 'और'): keep split ONLY if both sides look actionable
            prev_item = merged[-1]
            prev_ok = self._clause_looks_actionable(prev_item["text"])
            curr_ok = self._clause_looks_actionable(item["text"])

            # Exception: pure greeting/wake prefix before an actionable command ("Hi Pulsar, open chrome")
            if not prev_ok and curr_ok and re.fullmatch(
                r'(?:hi|hello|hey|namaste|ok|okay|please|pls|plz)(?:\s+pulsar)?[!.,]*',
                prev_item["text"].strip(),
                re.IGNORECASE,
            ):
                # Replace greeting prefix with the real command (single step!)
                merged[-1]["text"] = item["text"]
                continue

            if prev_ok and curr_ok:
                merged.append({
                    "text": item["text"],
                    "relation": item["relation"],
                    "delimiter": item["prev_delimiter"],
                    "explicit": False,
                })
            else:
                # Re-join noun conjunction / conversational comma back into previous clause
                sep = item["prev_delimiter"]
                if not sep:
                    sep = ", "
                elif not sep.startswith(" ") and not sep.startswith(","):
                    sep = " " + sep
                if not sep.endswith(" "):
                    sep = sep + " "
                merged[-1]["text"] = re.sub(r'\s+', ' ', f"{prev_item['text']}{sep}{item['text']}").strip()

        return merged

    def is_multi_step(self, command: str) -> bool:
        """
        Determine accurately if a command decomposes into 2+ executable steps.
        Protected against quotes ('type "hello, world and bye"'), numbers ('1,000'),
        noun conjunctions ('cats and dogs'), and conversational commas ('Hello, how are you?').
        """
        if not command or not command.strip():
            return False

        # Fast path: Dedicated atomic Tier-1 control intents are NEVER multi-step!
        atomic_intents = {
            'media_control', 'volume_control', 'check_taskbar', 'battery_status',
            'wifi_toggle', 'bluetooth_toggle', 'dark_mode_toggle', 'system_control',
            'executive_stop', 'executive_pause', 'executive_resume',
        }
        if getattr(self, 'intent_router', None):
            try:
                res = self.intent_router._fast_match(command)
                if res and res.tier == 1 and res.intent_name in atomic_intents:
                    return False
            except Exception:
                pass

        segments = self.split_with_relations(command)
        return len(segments) > 1

    def split_into_steps(self, command: str) -> List[str]:
        """Split command into individual step strings cleanly across Latin and Devanagari text."""
        segments = self.split_with_relations(command)
        if not segments:
            return [command.strip()] if command and command.strip() else []
        return [seg["text"] for seg in segments if seg["text"].strip()]

    # =========================================================================
    # STEP PARSING, AGENT MAPPING & PARAMETER ENHANCEMENT
    # =========================================================================

    def _infer_action_hints(self, intent: str, params: Dict[str, Any], text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Determine (execution_target, agent_id, capability) for a parsed step."""
        try:
            from ai_assistant.ai.intent_router import AGENT_INTENT_METADATA
            if intent in AGENT_INTENT_METADATA:
                aid, cap = AGENT_INTENT_METADATA[intent]
                return "agent", params.get("agent_id") or aid, params.get("capability") or cap
        except Exception:
            pass

        if intent == "create_document":
            doc_type = str(params.get("doc_type") or "document").lower()
            cap = "create_powerpoint" if doc_type in ("ppt", "pptx", "powerpoint", "presentation") else "create_word_document"
            return "agent", "productivity-001", params.get("capability") or cap

        if intent == "agent_task" or params.get("agent_id"):
            return "agent", params.get("agent_id"), params.get("capability")

        return "local", None, None

    def parse_single_step(self, step_text: str, step_number: int) -> TaskStep:
        """
        Parse a single command step using IntentRouter with Devanagari-safe regex fallback.
        """
        step_text_clean = step_text.strip()

        # 1. Try unified IntentRouter first
        if getattr(self, 'intent_router', None):
            try:
                res = self.intent_router.route(step_text_clean)
                if res and res.intent_name and res.intent_name not in ['conversational', 'info_query']:
                    params = dict(res.parameters or {})
                    params['text'] = step_text_clean
                    if 'target' in params and 'app_name' not in params:
                        params['app_name'] = params['target']

                    exec_target, agent_id, capability = self._infer_action_hints(res.intent_name, params, step_text_clean)
                    if exec_target == "agent":
                        params.setdefault("description", step_text_clean)
                        if agent_id:
                            params.setdefault("agent_id", agent_id)
                        if capability:
                            params.setdefault("capability", capability)

                    return TaskStep(
                        step=step_number,
                        step_id=f"step_{step_number}",
                        intent=res.intent_name,
                        params=params,
                        original_text=step_text_clean,
                        description=step_text_clean,
                        execution_target=exec_target,
                        agent_id=agent_id,
                        capability=capability,
                        output_key=f"step_{step_number}",
                        requires_confirmation=(res.intent_name == "system_control"),
                    )
            except Exception as e:
                logger.debug(f"Intent router in parse_single_step fallback: {e}")

        # 2. Fallback: Simple pattern matching on original & normalized text
        intent = 'unknown'
        params: Dict[str, Any] = {'text': step_text_clean}
        try:
            from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
            candidates = list(dict.fromkeys([step_text_clean, normalize_hinglish_devanagari(step_text_clean)]))
        except Exception:
            candidates = [step_text_clean]

        for candidate in candidates:
            if not candidate:
                continue
            for action, patterns in self.action_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, candidate, re.IGNORECASE | re.UNICODE)
                    if match:
                        intent = action
                        groups = match.groups()
                        params['matched_pattern'] = pattern
                        params['matches'] = groups
                        if action == 'open_app':
                            kw_words = {'kholo', 'khojo', 'open', 'start', 'launch', 'chalu', 'chalu karo', 'करो', 'खोलो'}
                            cands = [g for g in groups if g and g.lower().strip() not in kw_words]
                            if cands:
                                params['app_name'] = cands[0].strip()
                                params['target'] = cands[0].strip()
                        elif action == 'send_message':
                            kw_words = {'message', 'bhejo', 'send', 'bol do', 'भेजो'}
                            cands = [g for g in groups if g and g.lower().strip() not in kw_words]
                            if cands:
                                params['contact'] = cands[0].strip()
                        elif action == 'type_text' and groups:
                            params['text'] = groups[0].strip()
                        elif action == 'skip_time':
                            for g in groups:
                                if g and str(g).isdigit():
                                    params['minutes'] = int(g)
                                    break
                        break
                if intent != 'unknown':
                    break
            if intent != 'unknown':
                break

        exec_target, agent_id, capability = self._infer_action_hints(intent, params, step_text_clean)
        if intent == 'unknown' and self._clause_looks_actionable(step_text_clean):
            # Unknown actionable phrase (e.g. specialized task) can safely route to agent coordinator
            exec_target = "agent"
            params.setdefault("description", step_text_clean)

        return TaskStep(
            step=step_number,
            step_id=f"step_{step_number}",
            intent=intent,
            params=params,
            original_text=step_text_clean,
            description=step_text_clean,
            execution_target=exec_target,
            agent_id=agent_id,
            capability=capability,
            output_key=f"step_{step_number}",
        )

    def infer_dependencies(self, steps: List[TaskStep], relations: Optional[List[Dict[str, str]]] = None) -> List[TaskStep]:
        """
        Infer DAG dependencies, parallel groups, and fallback/conditional edges.
        Preserves sequential dependencies by default when no explicit parallel/fallback cue exists.
        """
        if not steps:
            return steps

        parallel_wave_counter = 0

        for idx, step in enumerate(steps):
            rel_info = relations[idx] if (relations and idx < len(relations)) else {"relation": "sequential"}
            relation = rel_info.get("relation", "sequential") if idx > 0 else "start"

            # 1. Explicit {step_N.*} or {prev.*} placeholder references add explicit dependencies
            explicit_deps: List[int] = []
            for val in (step.params or {}).values():
                if not isinstance(val, str):
                    continue
                for m in re.finditer(r'\{(?:step_?(\d+))\b[^}]*\}', val, re.IGNORECASE):
                    ref_num = int(m.group(1))
                    if 1 <= ref_num < step.step and ref_num not in explicit_deps:
                        explicit_deps.append(ref_num)
                if "{prev." in val or "{prev}" in val:
                    if idx > 0 and steps[idx - 1].step not in explicit_deps:
                        explicit_deps.append(steps[idx - 1].step)

            if idx == 0:
                step.dependencies = []
                continue

            prev_step = steps[idx - 1]

            if relation == "parallel":
                # Parallel step shares upstream dependencies with prev_step rather than depending on prev_step
                if not prev_step.parallel_group:
                    parallel_wave_counter += 1
                    group_name = f"wave_{parallel_wave_counter}"
                    prev_step.parallel_group = group_name
                step.parallel_group = prev_step.parallel_group
                step.dependencies = list(explicit_deps) if explicit_deps else list(prev_step.dependencies)

            elif relation == "conditional_fallback":
                # Previous step triggers this step ONLY on failure
                prev_step.on_failure = "fallback"
                prev_step.fallback_step = step.step
                step.condition = "on_failure"
                step.dependencies = [prev_step.step]

            else:
                # Sequential: depend on previous step unless it belongs to a closing parallel wave,
                # in which case fan-in on all steps in that parallel wave!
                if prev_step.parallel_group:
                    wave_members = [s.step for s in steps[:idx] if s.parallel_group == prev_step.parallel_group]
                    deps = list(dict.fromkeys([*wave_members, *explicit_deps]))
                else:
                    deps = list(dict.fromkeys([prev_step.step, *explicit_deps]))
                step.dependencies = deps

        return steps

    def parse_command(self, command: str) -> List[TaskStep]:
        """
        Parse a command into TaskStep DAG with dependencies, parallel groups, and agent hints.
        """
        logger.info(f"Parsing command: {command}")
        if not command or not command.strip():
            return []

        # If atomic / not multi-step, parse directly as a single step (zero multi-step splitting)
        if not self.is_multi_step(command):
            step = self.parse_single_step(command.strip(), 1)
            step = self.enhance_step_params(step, command.strip(), step_index=0, all_steps=[step])
            return [step]

        segments = self.split_with_relations(command)
        if not segments:
            return [self.parse_single_step(command, 1)]

        if len(segments) == 1:
            step = self.parse_single_step(segments[0]["text"], 1)
            step = self.enhance_step_params(step, command, step_index=0, all_steps=[step])
            return [step]

        logger.debug(f"Split into {len(segments)} steps: {[s['text'] for s in segments]}")

        steps: List[TaskStep] = []
        for i, seg in enumerate(segments, start=1):
            step = self.parse_single_step(seg["text"], i)
            steps.append(step)

        for idx, step in enumerate(steps):
            steps[idx] = self.enhance_step_params(step, command, step_index=idx, all_steps=steps)

        # Drop leading non-actionable preamble steps (e.g. "i want to research on smtg", "listen pulsar")
        # when subsequent concrete executable steps exist
        if len(steps) > 1:
            actionable_subsequent = [s for s in steps[1:] if s.intent not in ('unknown', 'conversational', 'info_query', None)]
            if actionable_subsequent:
                first_text = (steps[0].original_text or "").lower().strip()
                is_preamble = (
                    steps[0].intent in ('unknown', 'conversational', 'info_query', None)
                    or bool(re.match(r'^(?:i\s+(?:want|need|wish)\s+to|main\s+(?:chahta|chahti)\s+hoon|mujhe\s+.*karna\s+hai|ek\s+kaam\s+karo|sun|suno)\b', first_text))
                )
                if is_preamble:
                    logger.info(f"Dropping conversational preamble step: '{steps[0].original_text}' ({steps[0].intent})")
                    steps = steps[1:]
                    segments = segments[1:]

        # Collapse duplicate adjacent read-only list_running_apps / check_taskbar steps
        deduped_steps: List[TaskStep] = []
        deduped_segs: List[Dict[str, Any]] = []
        taskbar_intents = {'list_running_apps', 'check_taskbar'}
        for idx, s in enumerate(steps):
            if deduped_steps and s.intent in taskbar_intents and deduped_steps[-1].intent in taskbar_intents:
                deduped_steps[-1].intent = 'list_running_apps'
                continue
            deduped_steps.append(s)
            if idx < len(segments):
                deduped_segs.append(segments[idx])
        steps = deduped_steps
        segments = deduped_segs

        # Renumber steps after dropping/collapsing
        for i, s in enumerate(steps, start=1):
            s.step = i
            s.step_id = f"step_{i}"
            s.output_key = f"step_{i}"

        # Forward Chrome profile context from earlier open_app steps to dependent search/media steps
        inherited_profile = None
        for s in steps:
            if s.intent == 'open_app' and s.params.get('profile'):
                inherited_profile = s.params['profile']
            elif inherited_profile and s.intent in ['youtube_search', 'search_web', 'play_media', 'play_video', 'youtube_history']:
                if not s.params.get('profile'):
                    s.params['profile'] = inherited_profile

        # Infer DAG dependencies, parallel groups, and fallback edges
        steps = self.infer_dependencies(steps, relations=segments)

        logger.info(f"Parsed {len(steps)} steps with DAG dependencies")
        return steps

    def extract_message_content(self, command: str) -> Optional[str]:
        """Extract message body from a command or step clause (Unicode/Devanagari safe)."""
        patterns = [
            r'(?:message|msg|भेजो|send|text).*?(?:कि|ki|that|saying|:)\s+(.+)',
            r'(?:बोल|bol|tell).*?(?:कि|ki|that)\s+(.+)',
            r'(?:message|msg|भेजो|send)\s+["\'](.+?)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE | re.UNICODE)
            if match:
                return match.group(1).strip()
        return None

    def extract_contact_name(self, command: str) -> Optional[str]:
        """Extract contact/recipient name cleanly across Latin & Devanagari combining marks."""
        patterns = [
            r'([^\s,]+?)\s+को\s+(?:message|msg|भेजो|send|बोल)',
            r'([^\s,]+?)\s+ko\s+(?:message|msg|bhejo|send|bol)',
            r'(?:message|msg|भेजो|send|text)\s+(?:to\s+)?([^\s,:]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE | re.UNICODE)
            if match:
                cand = match.group(1).strip()
                if cand.lower() not in {"to", "on", "via", "ki", "that", "saying"}:
                    return cand
        return None

    def enhance_step_params(
        self,
        step: TaskStep,
        full_command: str,
        step_index: int = 0,
        all_steps: Optional[List[TaskStep]] = None,
    ) -> TaskStep:
        """Enhance step parameters with extracted info, dynamic Chrome profile lookup, and {prev.output} wiring."""
        step_text = step.original_text or ""

        if step.intent == 'send_message':
            contact = self.extract_contact_name(step_text)
            if contact:
                step.params['contact'] = contact
            # Extract from THIS step first (prevents step 2 from overwriting step 1's message!)
            message = self.extract_message_content(step_text)
            if not message and (all_steps is None or step_index == len(all_steps) - 1):
                message = self.extract_message_content(full_command)
            if message:
                step.params['message'] = message

        elif step.intent == 'open_app':
            target = str(step.params.get('target') or step.params.get('app_name') or '').strip()
            # Dynamic Chrome profile detection via automation.browser_profiles (never hardcoded list!)
            if target:
                try:
                    from ai_assistant.automation.browser_profiles import (
                        extract_profile_from_text,
                        resolve_chrome_profile,
                    )
                    extracted_prof, _ = extract_profile_from_text(target)
                    resolved = extracted_prof or (
                        target.lower().replace('profile', '').strip()
                        if 'profile' in target.lower() and resolve_chrome_profile(target)
                        else None
                    )
                    if not resolved and resolve_chrome_profile(target):
                        resolved = target.lower().strip()
                    if resolved:
                        step.params['profile'] = resolved.lower().strip()
                        step.params['target'] = resolved.title() if 'profile' not in target.lower() else target.title()
                        step.params['app_name'] = step.params['target']
                except Exception:
                    pass

        elif step.intent in ['youtube_search', 'search_web']:
            q = step.params.get('query') or ''
            if q:
                cleaned = re.sub(r'^(?:for|of)\s+', '', str(q), flags=re.IGNORECASE)
                cleaned = re.sub(
                    r'\b(on\s+youtube|in\s+youtube|youtube\s+pe|youtube\s+par)\b',
                    '',
                    cleaned,
                    flags=re.IGNORECASE,
                ).strip()
                step.params['query'] = cleaned

        elif step.intent == 'type_text':
            raw_t = step.params.get('text') or ''
            if isinstance(raw_t, str) and len(raw_t) >= 2:
                if (raw_t.startswith('"') and raw_t.endswith('"')) or (raw_t.startswith("'") and raw_t.endswith("'")):
                    step.params['text'] = raw_t[1:-1]

        # Context / pronoun wiring for follow-up steps (step_index > 0)
        if step_index > 0:
            if step.intent in ('agent_writer', 'create_document') and _CONTEXT_PREV_OUTPUT_RE.search(step_text):
                if step.intent == 'agent_writer':
                    topic = str(step.params.get('topic') or '')
                    if not topic or topic.lower() in ('it', 'this', 'that', 'the result', 'the output', 'the research'):
                        step.params['topic'] = '{prev.output}'
                    elif '{prev.output}' not in step.params.get('description', ''):
                        step.params['context_input'] = '{prev.output}'
                elif step.intent == 'create_document':
                    step.params.setdefault('content', '{prev.output}')
            elif step.intent in ('move_file', 'send_file') and _CONTEXT_PREV_OUTPUT_RE.search(step_text):
                src_key = 'source' if step.intent == 'move_file' else 'file'
                cur_val = str(step.params.get(src_key) or '').lower().strip()
                if not cur_val or cur_val in ('it', 'this', 'that', 'the file'):
                    step.params[src_key] = '{prev.path}'

        return step


def parse_multi_step_command(command: str) -> List[TaskStep]:
    """Parse a multi-step command into task steps."""
    parser = MultiStepCommandParser()
    return parser.parse_command(command)
