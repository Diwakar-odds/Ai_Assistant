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
                        last_updated TEXT NOT NULL,
                        embedding BLOB
                    )
                """)
                # Handle existing tables that lack the embedding column
                try:
                    conn.execute("ALTER TABLE user_dna ADD COLUMN embedding BLOB")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error initializing User DNA database: {e}")

    def update_trait(self, key: str, value: Any, confidence: float = 1.0):
        """Update a specific trait in the User's DNA with its vector embedding."""
        try:
            now_iso = datetime.now().isoformat()
            val_json = json.dumps(value)

            blob = None
            try:
                from ai_assistant.ai.shared_embedder import encode_text
                import numpy as np
                trait_text = f"{key}: {value}"
                vec = encode_text(trait_text, normalize=True)
                if vec is not None:
                    blob = vec.astype(np.float16).tobytes()
            except Exception:
                blob = None

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_dna (key, value, confidence, last_updated, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        confidence = excluded.confidence,
                        last_updated = excluded.last_updated,
                        embedding = excluded.embedding
                """, (key, val_json, confidence, now_iso, blob))
        except Exception as e:
            logger.error(f"Error updating User DNA trait '{key}': {e}")

    def search_traits_by_vector(self, query: str, limit: int = 3, min_score: float = 0.35) -> List[Dict[str, Any]]:
        """Search user traits using vector similarity against SQLite BLOB embeddings."""
        clean_q = str(query or "").strip()
        if not clean_q:
            return []
        try:
            from ai_assistant.ai.shared_embedder import encode_text
            import numpy as np

            q_vec = encode_text(clean_q, normalize=True)
            if q_vec is None:
                return []

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, confidence, embedding FROM user_dna WHERE embedding IS NOT NULL")
                rows = cursor.fetchall()
                if not rows:
                    return []

                raw_blobs = b"".join(bytes(r[3]) for r in rows if r[3])
                num_rows = len(raw_blobs) // 768
                if num_rows == 0:
                    return []

                matrix = np.frombuffer(raw_blobs[:num_rows * 768], dtype=np.float16).reshape(num_rows, 384).astype(np.float32)
                scores = np.dot(matrix, q_vec)
                ranked_indices = np.argsort(scores)[::-1]

                results = []
                for idx in ranked_indices:
                    score = float(scores[idx])
                    if score < min_score:
                        break
                    row = rows[idx]
                    try:
                        val = json.loads(row[1])
                    except Exception:
                        val = row[1]
                    results.append({
                        "key": row[0],
                        "value": val,
                        "confidence": row[2],
                        "score": round(score, 3),
                    })
                    if len(results) >= limit:
                        break
                return results
        except Exception as e:
            logger.debug(f"UserDNA vector search warning: {e}")
            return []

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
        
        try:
            from ai_assistant.knowledge.personal_knowledge_graph import get_knowledge_graph
            pkg = get_knowledge_graph()
            # Fetch generic context based on "user" to grab general relations
            graph_context = pkg.get_context_for_command("user my")
            if graph_context:
                context_parts.append(graph_context)
        except Exception as e:
            logger.error(f"Failed to fetch PKG context in UserDNA: {e}")
        
        # Group by category if possible or just list them
        relationships = []
        preferences = []
        work = []
        hobbies = []
        events = []
        habits = []
        
        for k, v in profile.items():
            if k == "user_name": continue
            if "upcoming" in k or "exam" in k or "event" in k or "deadline" in k:
                events.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "habit" in k or "routine" in k:
                habits.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "name" in k or "friend" in k or "spouse" in k or "partner" in k:
                relationships.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "like" in k or "favorite" in k or "prefer" in k:
                preferences.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "job" in k or "work" in k or "role" in k:
                work.append(f"{k.replace('_', ' ').title()}: {v}")
            elif "hobby" in k or "interest" in k or "play" in k:
                hobbies.append(f"{k.replace('_', ' ').title()}: {v}")
                
        if events: context_parts.append("Upcoming Events & Deadlines: " + ", ".join(events))
        if habits: context_parts.append("Work & Lifestyle Habits: " + ", ".join(habits))
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
            "user_name": r"(?:my name is|call me|you can call me|mera naam|naam hai|मेरा नाम|नाम है)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| and| but| hai| है)",
            "friend_name": r"(?:my friend'?s name is|my (?:best )?friend is|mera dost|mere dost ka naam|mere dost|मेरा दोस्त|मेरे दोस्त का नाम)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| hai| tha| है| था)",
            "upcoming_exam": r"(?:my (?:exam|paper|test) is on|my (?:exam|paper|test) is|mera (?:exam|paper|test|pariksha)|मेरा (?:एग्जाम|पेपर|टेस्ट|परीक्षा))\s+([a-zA-Z0-9\u0900-\u097F\s]+?)(?:\.|!|,|$| ko| pe| par| hai| है)",
            "spouse_name": r"(?:my (?:wife|husband|spouse|partner)'?s name is|my (?:wife|husband|spouse|partner) is)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "pet_name": r"(?:my (?:dog|cat|pet)'?s name is|my (?:dog|cat|pet) is)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "boss_name": r"(?:my boss'?s name is|my manager is|my boss is)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "user_location": r"(?:i live in|i am from|i'm from|based in)\s+([a-zA-Z0-9\u0900-\u097F\s,]+?)(?:\.|!|,|$| and| but)|(?:mai|main|me|hum|मैं)\s+([a-zA-Z0-9\u0900-\u097F\s]+?)\s+(?:me|mein|में)\s+(?:rehta|rehti|rehte|रहता|रहती|रहते)\s+(?:hu|hoon|hूँ|हूँ|hai|है)",
            "workplace": r"(?:i work at|i work for|my company is|mai kaam karta hu)\s+([a-zA-Z0-9\u0900-\u097F\s,]+?)(?:\.|!|,|$| and| me| mein)",
            "job_title": r"(?:i am a|i work as a|i'm a)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| and| at)",
            "favorite_color": r"(?:my favorite color is|mera favorite color|mera pasandida rang|i love the color|मेरा पसंदीदा रंग)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| hai| है)",
            "favorite_food": r"(?:my favorite food is|mera favorite khana|i love eating|i love to eat|मेरा पसंदीदा खाना)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| hai| है)",
            "favorite_drink": r"(?:my favorite drink is|i love drinking|i prefer to drink)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$| hai)",
            "hobby": r"(?:my hobby is|i like to|i love to|in my free time i)\s+([a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "dietary_restriction": r"(?:i am allergic to|i can't eat|i don't eat|i am a)\s+(vegan|vegetarian|gluten free|[a-zA-Z\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "wake_up_time": r"(?:i usually wake up at|i wake up at)\s+([0-9:amp\s]+?)(?:\.|!|,|$)",
            "sleep_time": r"(?:i usually sleep at|i go to bed at)\s+([0-9:amp\s]+?)(?:\.|!|,|$)",
            "vehicle": r"(?:i drive a|my car is a|my bike is a)\s+([a-zA-Z0-9\s]+?)(?:\.|!|,|$)",
            "language_spoken": r"(?:i speak|i can speak)\s+([a-zA-Z\s]+?)(?:\.|!|,|$)",
            "music_preference": r"(?:i like listening to|my favorite music is|i love)\s+([a-zA-Z\u0900-\u097F\s]+?)\s+(?:music|songs)",
            "birthday": r"(?:my birthday is on|i was born on)\s+([a-zA-Z0-9\s]+?)(?:\.|!|,|$)",
            "current_project": r"(?:i am working on|my current project is)\s+([a-zA-Z0-9\u0900-\u097F\s]+?)(?:\.|!|,|$)",
            "tool_preference": r"(?:i prefer using|i use)\s+([a-zA-Z0-9\s]+?)\s+(?:for|to)"
        }
        
        for trait_key, regex_pattern in patterns.items():
            match = re.search(regex_pattern, text_lower, re.IGNORECASE | re.UNICODE)
            if match:
                raw_val = next((g for g in match.groups() if g), "")
                value = str(raw_val).strip().title()
                # Clean trailing punctuation, small filler words, and 'hai'
                value = re.sub(r'\b(hai|hain|hu|hoon|the|a|an|is|was|my|it|ko|par|pe|है|था|थी|को|पर)\b', '', value, flags=re.IGNORECASE | re.UNICODE).strip()
                value = re.sub(r'[^\w\u0900-\u097F\s]', '', value).strip()
                
                # Sanity check
                if len(value) > 1 and value.lower() not in ["the", "a", "an", "is", "was", "my", "it", "hai"]:
                    self.update_trait(trait_key, value)
                    found_fact = True
                    logger.debug(f"UserDNA Extracted Fact: {trait_key} = {value}")
            
        return found_fact
