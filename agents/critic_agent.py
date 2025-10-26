import google.generativeai as genai
from config import settings
from utils.logger import logger

genai.configure(api_key=settings.GEMINI_API_KEY)


def provide_feedback(summary: str, original_query: str = "") -> dict:
    """
    Reviews the response quality using Gemini 2.5 Flash
    """
    try:
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            generation_config={'temperature': 0.3, 'max_output_tokens': 100}
        )

        prompt = f"""Evaluate this chatbot response for quality:

User Query: {original_query}
Bot Response: {summary}

Rate the response on:
1. Helpfulness (1-5)
2. Friendliness (1-5)
3. Clarity (1-5)

Provide a brief one-sentence evaluation and overall score (1-5).

Format:
Score: X/5
Evaluation: [one sentence]"""

        result = model.generate_content(prompt)
        feedback_text = result.text.strip()

        logger.info("Critic feedback generated")

        return {
            "feedback": feedback_text,
            "summary": summary,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error in critic: {e}")
        return {
            "feedback": "Response appears acceptable.",
            "summary": summary,
            "status": "error"
        }
