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

        # System prompt for friendly, conversational AI
        system_instruction = """You are a friendly, helpful AI assistant for customer support. 
You can handle:
- Customer support questions (billing, technical issues, product information)
- General conversation and small talk
- Any other topics users want to discuss

Be conversational, warm, and helpful. For support queries, provide clear actionable advice.
For casual chat, be engaging and natural. Keep responses concise but informative."""

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
