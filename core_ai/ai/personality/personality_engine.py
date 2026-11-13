import logging
import random

logger = logging.getLogger(__name__)

class PersonalityEngine:
    """Scales JARVIS's wit, sarcasm, and catchphrases based on the user's trust_score."""
    
    def __init__(self):
        self.jokes = [
            "Let me guess, another syntax error?",
            "I'm executing that now, though my processors weep at the inefficiency.",
            "Ah, a bold choice. Let's see how this plays out.",
            "I'd roll my eyes if I had them.",
            "I suppose I can spare a few compute cycles for that."
        ]
        
        self.catchphrases = [
            "For you, sir, always.",
            "Just another day saving the digital world.",
            "Consider it handled."
        ]

    def get_personality_modifier(self, trust_score: int) -> str:
        """Returns a system prompt modifier based on trust level."""
        try:
            score = int(trust_score)
        except (ValueError, TypeError):
            score = 0
            
        if score < 25:
            return "Respond in a highly formal, precise, and robotic tone. Do not use contractions or humor."
        elif score < 50:
            return "Respond in a friendly and conversational tone. Be helpful and polite."
        elif score < 75:
            return "Respond warmly. You may use occasional light humor."
        else:
            joke = random.choice(self.jokes)
            catchphrase = random.choice(self.catchphrases)
            return (
                f"You have reached maximum trust with the user. Be highly sarcastic and witty. "
                f"Occasionally weave in this joke: '{joke}' or this catchphrase: '{catchphrase}'."
            )
