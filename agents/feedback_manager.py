import json
import os
from datetime import datetime
from config import settings
from utils.logger import logger


def save_feedback(feedback_text: str, query: str = "", response: str = "") -> bool:
    """
    Save user feedback to a JSON file
    """
    try:
        feedback_file = settings.FEEDBACK_STORE

        # Load existing feedback
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        else:
            feedback_data = []

        # Add new feedback entry
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "feedback": feedback_text,
            "query": query,
            "response": response
        }

        feedback_data.append(feedback_entry)

        # Save updated feedback
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Feedback saved successfully")
        return True

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return False


def get_all_feedback() -> list:
    """
    Retrieve all stored feedback
    """
    try:
        feedback_file = settings.FEEDBACK_STORE

        if os.path.exists(feedback_file):
            with open(feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []

    except Exception as e:
        logger.error(f"Error loading feedback: {e}")
        return []
