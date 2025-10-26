# CustomerSupportAI

A full-featured multi-agent customer support chatbot built using FastAPI, LangGraph, and multiple LLM utilities.

## Setup

1. Clone the repository
2. Run `setup.sh` (or manually `pip install -r requirements.txt`)
3. Create and update your `.env` file with required keys and config
4. Start the API server:
    ```
    uvicorn app:app --reload
    ```
5. Access the chat interface at [http://localhost:8000](http://localhost:8000)

## File Structure
- `app.py` — Main FastAPI server
- `agents/` — Routing, summarizer, critic, feedback managers
- `researchers/` — Query handler modules
- `llms/` — LLM classifier, analyzer, prioritizer modules
- `database/` — DB and feedback storage
- `frontend/` — Web templates, static assets, GUI
- `utils/` — Logging and helper utilities

## Testing

Run test scripts (see `tests/`) for key components.

---

For any environment-specific questions or deployment setup (Dockerfile, cloud configs, etc), just ask!
