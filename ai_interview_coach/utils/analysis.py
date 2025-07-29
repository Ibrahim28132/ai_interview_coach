import logging
from typing import Dict, Any
from config import Config

def analyze_audio_features(text: str) -> Dict[str, Any]:
    try:
        if not Config.VOICE_ENABLED:
            return {
                "word_count": 0,
                "filler_words": 0,
                "pace": 5,
                "confidence": 5,
                "estimated_tone": "neutral"
            }

        words = text.split()
        word_count = len(words)
        filler_words = sum(1 for word in words if word.lower() in
                           ["um", "uh", "like", "you know", "ah"])

        pace = min(10, max(1, int((word_count / 10) * 6)))
        confidence = max(1, min(10, 10 - (filler_words * 2)))

        return {
            "word_count": word_count,
            "filler_words": filler_words,
            "pace": pace,
            "confidence": confidence,
            "estimated_tone": "neutral"
        }
    except Exception as e:
        logging.error(f"Error analyzing audio features: {e}")
        return {
            "word_count": 0,
            "filler_words": 0,
            "pace": 5,
            "confidence": 5,
            "estimated_tone": "neutral"
        }