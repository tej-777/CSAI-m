from researchers.main_researcher import handle_universal_query
from utils.logger import logger


def route_query(query: str, conversation_history: list = None) -> dict:
    """
    Simplified router - sends all queries to universal researcher
    No more topic classification needed!
    """
    try:
        logger.info(f"Routing query to universal researcher: {query[:50]}...")

        # Direct all queries to the universal researcher
        result = handle_universal_query(query, conversation_history)

        return result

    except Exception as e:
        logger.error(f"Error in router: {e}")
        return {
            "response": "I encountered an error. Please try again.",
            "query": query,
            "status": "error"
        }
