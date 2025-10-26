from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from agents.router_agent import route_query
from agents.summarizer_agent import summarize_output
from agents.critic_agent import provide_feedback
from agents.feedback_manager import save_feedback
from utils.logger import logger
from config import settings

app = FastAPI(title="Customer Support AI Chatbot")

# Serve static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Session storage for conversation history (in production, use Redis/DB)
conversations = {}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index_modern.html", {"request": request})


@app.post("/query")
async def handle_query(request: Request):
    try:
        logger.info("Handling query")
        data = await request.json()
        query = data.get("query", "")
        session_id = data.get("session_id", "default")

        if not query.strip():
            return JSONResponse({"summary": "", "feedback": "Empty query"}, status_code=400)

        # Get conversation history
        history = conversations.get(session_id, [])

        # Route to universal researcher
        routed = route_query(query, history)

        # Summarize
        summary = summarize_output(routed)

        # Get critic feedback
        critic_result = provide_feedback(summary, query)
        feedback = critic_result.get("feedback", "")

        # Update conversation history
        if session_id not in conversations:
            conversations[session_id] = []
        conversations[session_id].append({"user": query, "bot": summary})

        # Keep only last 10 exchanges
        if len(conversations[session_id]) > 10:
            conversations[session_id] = conversations[session_id][-10:]

        logger.info("Query handled successfully")
        return JSONResponse({"summary": summary, "feedback": feedback})

    except Exception as e:
        logger.error(f"Error handling /query request: {e}", exc_info=True)
        return JSONResponse(
            {"summary": "I encountered an error. Please try again.", "feedback": ""},
            status_code=500
        )


@app.post("/feedback")
async def handle_feedback(request: Request):
    try:
        data = await request.json()
        feedback_text = data.get("feedback", "")
        query = data.get("query", "")
        response = data.get("response", "")

        success = save_feedback(feedback_text, query, response)

        if success:
            return JSONResponse({"status": "success"})
        else:
            return JSONResponse({"status": "error"}, status_code=500)

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return JSONResponse({"status": "error"}, status_code=500)


@app.get("/api/history")
async def get_history():
    # Return recent conversation for a session
    # In production, fetch from database
    return JSONResponse({"history": []})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
