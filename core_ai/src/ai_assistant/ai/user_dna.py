import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import re
from ai_assistant.core.database_config import get_db_path

logger = logging.getLogger(__name__)

class UserDNA:
    """
    User DNA System for maintaining a long-term evolutionary profile of the user.
    Integrates static onboarding preferences with dynamic implicit feedback.
    """
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(get_db_path('personal_knowledge'))
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_dna (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        last_updated TEXT NOT NULL
                    )
                """)
        except Exception as e:
            logger.error(f"Error initializing User DNA database: {e}")

    def update_trait(self, key: str, value: Any, confidence: float = 1.0):
        """Update a specific trait in the User's DNA."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_dna (key, value, confidence, last_updated)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        confidence = excluded.confidence,
                        last_updated = excluded.last_updated
                """, (key, json.dumps(value), confidence, datetime.now().isoformat()))
        except Exception as e:
            logger.error(f"Error updating User DNA trait '{key}': {e}")

    def get_trait(self, key: str) -> Any:
        """Retrieve a specific trait."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM user_dna WHERE key=?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Error retrieving User DNA trait '{key}': {e}")
        return None

    def get_full_profile(self) -> Dict[str, Any]:
        """Get the complete user DNA profile."""
        profile = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM user_dna")
                rows = cursor.fetchall()
                for key, value_str in rows:
                    profile[key] = json.loads(value_str)
        except Exception as e:
            logger.error(f"Error retrieving full User DNA profile: {e}")
        return profile

    def incorporate_onboarding_data(self, onboarding_data: Dict[str, Any]):
        """Incorporate static onboarding preferences into the living DNA."""
        for key, value in onboarding_data.items():
            self.update_trait(key, value, confidence=1.0)

    def get_relationship_context(self) -> str:
        """Builds a mini-profile summary for LLM system prompt injection."""
        profile = self.get_full_profile()
        if not profile:
            return "No personal context available."
            
        context_parts = []
        name = profile.get("user_name", "User")
        context_parts.append(f"User Name: {name}")
        
        # Group by category if possible or just list them
        relationships = []
        preferences = []
        work = []
        hobbies = []
        
        for k, v in profile.items():
            if k == "user_name": continue
            if "name" in k or "friend" in k or "spouse" in k or "partner" in k:
                relationships.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "like" in k or "favorite" in k or "prefer" in k:
                preferences.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "job" in k or "work" in k or "role" in k:
                work.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "hobby" in k or "interest" in k or "play" in k:
                hobbies.append(f"{k.replace('_', ' ').title()}: {v}")
                
        if work: context_parts.append("Professional: " + ", ".join(work))
        if relationships: context_parts.append("Relationships: " + ", ".join(relationships))
        if preferences: context_parts.append("Preferences: " + ", ".join(preferences))
        if hobbies: context_parts.append("Hobbies: " + ", ".join(hobbies))
        
        return " | ".join(context_parts)

    def decay_confidence(self, decay_factor: float = 0.9, threshold: float = 0.1):
        """Reduces confidence of facts not confirmed recently (Ebbinghaus style)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Multiply confidence by decay_factor
                conn.execute("""
                    UPDATE user_dna 
                    SET confidence = confidence * ?
                """, (decay_factor,))
                
                # Optionally delete traits that fall below the threshold
                conn.execute("""
                    DELETE FROM user_dna WHERE confidence < ?
                """, (threshold,))
            logger.info("Applied confidence decay to User DNA.")
        except Exception as e:
            logger.error(f"Error decaying confidence: {e}")

    def extract_facts_from_text(self, text: str) -> bool:
        """Extract personal facts from text using 20+ robust patterns and save to DNA."""
        text_lower = text.lower()
        found_fact = False
        
        patterns = {
            "user_name": r"(?:my name is|call me|i am|i'm)\s+([a-zA-Z\s]+?)(?:\.|!|,|$| and| but)",
            "friend_name": r"(?:my friend'?s name is|my friend is)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "spouse_name": r"(?:my (?:wife|husband|spouse|partner)'?s name is|my (?:wife|husband|spouse|partner) is)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "pet_name": r"(?:my (?:dog|cat|pet)'?s name is|my (?:dog|cat|pet) is)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "boss_name": r"(?:my boss'?s name is|my manager is|my boss is)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "user_location": r"(?:i live in|i am from|i'm from|based in)\s+([a-zA-Z\s,]+?)(?:\.|!|,|$| and| but)",
            "workplace": r"(?:i work at|i work for|my company is)\s+([a-zA-Z0-9\s,]+?)(?:\.|!|,|$| and)",
            "job_title": r"(?:i am a|i work as a|i'm a)\s+([a-zA-Z\s]+?)(?:\.|!|,|$| and| at)",
            "favorite_color": r"(?:my favorite color is|i love the color)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "favorite_food": r"(?:my favorite food is|i love eating|i love to eat)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "favorite_drink": r"(?:my favorite drink is|i love drinking|i prefer to drink)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "hobby": r"(?:my hobby is|i like to|i love to|in my free time i)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "dietary_restriction": r"(?:i am allergic to|i can't eat|i don't eat|i am a)\s+(vegan|vegetarian|gluten free|[a-zA-Z\s]+?)(?:\.|!|,|$)",
            "wake_up_time": r"(?:i usually wake up at|i wake up at)\s+([0-9:amp\s]+?)(?:\.|!|,|$)",
            "sleep_time": r"(?:i usually sleep at|i go to bed at)\s+([0-9:amp\s]+?)(?:\.|!|,|$)",
            "vehicle": r"(?:i drive a|my car is a|my bike is a)\s+([a-zA-Z0-9\s]+?)(?:\.|!|,|$)",
            "language_spoken": r"(?:i speak|i can speak)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "music_preference": r"(?:i like listening to|my favorite music is|i love)\s+([a-zA-Z\s]+?)\s+(?:music|songs)",
            "birthday": r"(?:my birthday is on|i was born on)\s+([a-zA-Z0-9\s]+?)(?:\.|!|,|$)",
            "current_project": r"(?:i am working on|my current project is)\s+([a-zA-Z0-9\s]+?)(?:\.|!|,|$)",
            "tool_preference": r"(?:i prefer using|i use)\s+([a-zA-Z0-9\s]+?)\s+(?:for|to)"
        }
        
        for trait_key, regex_pattern in patterns.items():
            match = re.search(regex_pattern, text_lower, re.IGNORECASE)
            if match:
                value = match.group(1).strip().title()
                # Clean trailing punctuation and small filler words
                value = re.sub(r'[^\w\s]', '', value).strip()
                
                # Sanity check to avoid matching filler responses like "I like to" matching "sleep" but not completely.
                if len(value) > 1 and value.lower() not in ["the", "a", "an", "is", "was", "my", "it"]:
                    self.update_trait(trait_key, value)
                    found_fact = True
                    logger.debug(f"UserDNA Extracted Fact: {trait_key} = {value}")
            
        return found_fact
