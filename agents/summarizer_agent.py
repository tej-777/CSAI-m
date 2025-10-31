import google.generativeai as genai
from config import settings
from utils.logger import logger
import uuid

# Force API key flow (not ADC) and use REST transport
genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")


def summarize_output(routing_result: dict) -> str:
    """
    Summarizes and polishes the researcher's response using Gemini 2.5 Flash
    """
    try:
        response_text = routing_result.get("response", "")
        is_resummarize = bool(routing_result.get("resummarize", False))
        feedback_guidance = routing_result.get("feedback_guidance")

        # Always run through the formatter to enforce structure

        # Ask Gemini to polish/summarize. Use higher temperature on resummarize to get variation
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0.8 if is_resummarize else 0.3,
                'max_output_tokens': 400,
            }
        )

        style_id = str(uuid.uuid4()) if is_resummarize else ""
        guidance_block = f"\n\nUser feedback to consider (address these explicitly and avoid previous issues):\n{feedback_guidance}" if feedback_guidance else ""
        prompt = f"""You are refining an assistant answer for customer support. Make it structured, scannable, and helpful. Use Markdown formatting.
Formatting rules (STRICT):
- Output MUST use these sections in this exact order and with these exact headings:
  1. Summary
  2. Steps (if the task is procedural) OR Key Points (if not procedural). Choose ONE of these headings.
  3. Tips/Notes
  4. Next Steps / Resources
- Use short paragraphs (2-3 sentences max).
- Use numbered steps for the Steps section; use bullet points for Key Points.
- Keep it concise; avoid walls of text.
- Do not invent details; preserve meaning.
- Prefer plain Markdown; never wrap the whole answer in a code block.
{"Provide an alternate phrasing different from earlier versions." if is_resummarize else ""}
{"Style ID: " + style_id if is_resummarize else ""}
{guidance_block}

Original response:
{response_text}

Return ONLY the final structured Markdown with those sections, nothing else."""

        result = model.generate_content(prompt)

        # Safely extract text, since result.text can fail when no valid Part exists
        summary = None
        try:
            if getattr(result, 'text', None):
                summary = (result.text or "").strip()
        except Exception:
            summary = None

        if not summary:
            try:
                candidates = getattr(result, 'candidates', None) or []
                if candidates:
                    parts = getattr(candidates[0], 'content', None)
                    if parts and getattr(parts, 'parts', None):
                        texts = [getattr(p, 'text', '') for p in parts.parts]
                        summary = "\n".join([t for t in texts if t]).strip()
            except Exception:
                summary = None

        if not summary:
            logger.warning("Summarizer produced no text; falling back to original response")
            return response_text

        logger.info("Response summarized successfully")
        return summary

    except Exception as e:
        logger.error(f"Error in summarizer: {e}")
        return routing_result.get("response", "I'm having trouble right now. Please try again.")
