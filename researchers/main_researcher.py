import google.generativeai as genai
from config import settings
from utils.logger import logger

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)


def handle_universal_query(query: str, conversation_history: list = None) -> dict:
    """
    Universal researcher that handles ALL types of queries using Gemini 2.5 Flash
    """
    try:
        # Build conversation context
        context = ""
        if conversation_history:
            context = "\n".join(
                [f"User: {h['user']}\nBot: {h['bot']}" for h in conversation_history[-3:]])

        # System prompt for structured, helpful answers
        system_instruction = """You are a friendly, helpful AI assistant for customer support.
Return answers in clean, scannable Markdown like ChatGPT/Gemini.

Formatting (STRICT):
- Use clear sections in this order when applicable:
  1. Summary
  2. Steps (if procedural) OR Key Points (if not procedural)
  3. Tips/Notes
  4. Next Steps / Resources
- Use numbered steps for procedures; bullet points for key points.
- Keep paragraphs short (2-3 sentences). Avoid walls of text.
- Use fenced code blocks with language when showing commands or code (e.g., ```bash, ```python).
- Do not add code fences around entire answers; only for code/commands.
- Be concise and actionable; do not invent facts.
"""

        # Prepare the full prompt
        full_prompt = f"{system_instruction}\n\nConversation history:\n{context}\n\nUser: {query}\n\nAssistant:"

        # Use Gemini 2.5 Flash
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            generation_config={
                'temperature': 0.7,
                'max_output_tokens': 1024,
            }
        )

        response = model.generate_content(full_prompt)
        answer = response.text.strip()

        logger.info(f"Universal researcher handled query: {query[:50]}...")

        return {
            "response": answer,
            "query": query,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error in universal researcher: {e}")
        return {
            "response": "I'm having trouble processing that right now. Could you please rephrase your question?",
            "query": query,
            "status": "error",
            "error": str(e)
        }
