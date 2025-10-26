import google.generativeai as genai
from config import settings
from utils.logger import logger

genai.configure(api_key=settings.GEMINI_API_KEY)


def summarize_output(routing_result: dict) -> str:
    """
    Summarizes and polishes the researcher's response using Gemini 2.5 Flash
    """
    try:
        response_text = routing_result.get("response", "")

        # For short responses, return as-is
        if len(response_text) < 150:
            return response_text

        # For longer responses, ask Gemini to polish/summarize
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            generation_config={'temperature': 0.3, 'max_output_tokens': 200}
        )

        prompt = f"""Polish this customer support response to be clear, friendly, and concise:

{response_text}

Polished response:"""

        result = model.generate_content(prompt)
        summary = result.text.strip()

        logger.info("Response summarized successfully")
        return summary

    except Exception as e:
        logger.error(f"Error in summarizer: {e}")
        return routing_result.get("response", "I'm having trouble right now. Please try again.")
