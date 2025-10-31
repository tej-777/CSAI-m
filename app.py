from __future__ import annotations
def _heuristic_title_from_text(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "Untitled"
    # Take first sentence or first ~6 words
    for sep in ['.', '!', '?', '\n']:
        if sep in t:
            t = t.split(sep, 1)[0]
            break
    words = t.split()
    t = " ".join(words[:8])
    return t[:60] or "Untitled"

def _generate_chat_title(user_text: str, bot_text: str) -> str:
    try:
        # Best-effort: use Gemini via summarizer's model if available without heavy prompt
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            generation_config={'temperature': 0.2, 'max_output_tokens': 12}
        )
        prompt = f"""Create a 3-6 word chat title for this conversation topic.
User: {user_text}
Assistant: {bot_text}
Title:"""
        res = model.generate_content(prompt)
        title = None
        try:
            if getattr(res, 'text', None):
                title = (res.text or '').strip().strip('"')
        except Exception:
            title = None
        if not title:
            cands = getattr(res, 'candidates', None) or []
            if cands and getattr(cands[0], 'content', None) and getattr(cands[0].content, 'parts', None):
                parts = cands[0].content.parts
                texts = [getattr(p, 'text', '') for p in parts]
                title = " ".join([t for t in texts if t]).strip().strip('"')
        if title:
            return title[:60]
    except Exception:
        pass

# Placeholder; will initialize after imports are loaded
fs = None
attachments_col = None

def _safe_mime(filename: str, content_type: str = None) -> str:
    if content_type:
        return content_type
    guess = mimetypes.guess_type(filename or "")[0]
    return guess or "application/octet-stream"

def _extract_text_from_path(path: str, mime: str) -> str:
    try:
        text = ""
        if mime.startswith("image/"):
            try:
                from PIL import Image
                import pytesseract
                with Image.open(path) as im:
                    text = pytesseract.image_to_string(im)
            except Exception as e:
                logger.warning(f"Image OCR failed: {e}")
        elif mime == "application/pdf" or (path.lower().endswith('.pdf')):
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    pages = pdf.pages[:10]
                    parts = []
                    for p in pages:
                        try:
                            parts.append(p.extract_text() or "")
                        except Exception:
                            continue
                    text = "\n".join([t for t in parts if t])
            except Exception as e:
                logger.warning(f"PDF text extraction failed: {e}")
        elif mime.startswith("text/") or path.lower().endswith(('.txt', '.md', '.csv', '.log')):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read(200000)
            except Exception as e:
                logger.warning(f"Text read failed: {e}")
        return (text or "").strip()
    except Exception as e:
        logger.error(f"Attachment OCR error: {e}")
        return ""

def _store_gridfs_and_ocr(upload: UploadFile, chat_id: str) -> dict:
    if fs is None or attachments_col is None:
        raise RuntimeError("Attachments storage not initialized")
    fname = upload.filename or f"file-{uuid.uuid4()}"
    mime = _safe_mime(fname, upload.content_type)
    size = 0
    # Save to GridFS
    gridfs_id = None
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
                size += len(chunk)
        # Write from temp to GridFS stream
        with open(tmp_path, 'rb') as f:
            gridfs_id = fs.put(f, filename=fname, content_type=mime, metadata={"chat_id": chat_id, "size": size})
        # OCR
        ocr_text = _extract_text_from_path(tmp_path, mime)
        meta_doc = {
            "_id": gridfs_id,
            "chat_id": chat_id,
            "filename": fname,
            "mime": mime,
            "size": size,
            "ocr_text": (ocr_text[:200000] if ocr_text else ""),
            "createdAt": datetime.datetime.utcnow(),
        }
        attachments_col.replace_one({"_id": gridfs_id}, meta_doc, upsert=True)
        return {
            "id": str(gridfs_id),
            "name": fname,
            "mime": mime,
            "size": size,
        }
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass

def _get_attachment_snippets(chat_id: str, ids: list = None, limit: int = 3) -> str:
    try:
        if attachments_col is None:
            return ""
        q = {"chat_id": chat_id}
        if ids:
            try:
                q["_id"] = {"$in": [ObjectId(i) for i in ids if i]}
            except Exception:
                pass
        docs = list(attachments_col.find(q).sort("createdAt", -1).limit(limit))
        parts = []
        for d in docs:
            name = d.get("filename")
            mime = d.get("mime")
            txt = (d.get("ocr_text") or "").strip()
            if txt:
                snippet = txt[:600]
                parts.append(f"- {name} ({mime}):\n{snippet}")
        if parts:
            return "Attachment context:\n" + "\n\n".join(parts)
        return ""
    except Exception as e:
        logger.error(f"Failed to build attachment snippets: {e}")
        return ""

import os
import uuid
import datetime
import tempfile
import io
import mimetypes
from typing import List, Optional
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils.logger import logger
from config import settings
from database.db_manager import DatabaseManager
from agents.router_agent import route_query
from agents.summarizer_agent import summarize_output
from agents.critic_agent import provide_feedback
from agents.feedback_manager import save_feedback
import json

app = FastAPI(title="Customer Support AI Chatbot")

# Serve static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# Session storage for conversation history (in production, use Redis/DB)
conversations = {}

# Initialize Mongo/GridFS here (after imports and possibly settings/logger are loaded)
try:
    if 'settings' in globals():
        import pymongo
        import gridfs
        from bson import ObjectId  # noqa: F401
        mongo_client = pymongo.MongoClient(settings.MONGODB_URI)
        mongo_db = mongo_client[settings.MONGO_DB_NAME]
        fs = gridfs.GridFS(mongo_db)
        attachments_col = mongo_db.get_collection("attachments_meta")
except Exception as e:
    try:
        if 'logger' in globals():
            logger.error(f"Mongo/GridFS init failed (deferred): {e}")
    except Exception:
        pass

# Database manager for persistent history
db = DatabaseManager()

CHATS_FILE = "chats_data.json"

def _load_chats() -> list:
    try:
        if os.path.exists(CHATS_FILE):
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        return []
    except Exception:
        return []

def _save_chats(chats: list) -> None:
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as f:
            json.dump(chats, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
        chat_id = data.get("chat_id")
        attachment_ids = data.get("attachments") or []

        if not query.strip():
            return JSONResponse({"summary": "", "feedback": "Empty query"}, status_code=400)

        # Get conversation history (in-memory)
        history = conversations.get(session_id, [])

        # Load recent negative feedback for this chat to guide the next answer
        guided_query = query
        try:
            if chat_id:
                chats = _load_chats()
                for c in chats:
                    if c.get("id") == chat_id:
                        fbs = list(reversed(c.get("feedback", [])))[:5]
                        dislikes = [f for f in fbs if (f.get("rating") == "dislike")]
                        if dislikes:
                            parts = []
                            for i, f in enumerate(dislikes[:3], 1):
                                fb_txt = (f.get("feedback") or "").strip()
                                msg = (f.get("message") or "").strip()
                                if msg:
                                    msg = (msg[:220] + "…") if len(msg) > 220 else msg
                                if fb_txt:
                                    parts.append(f"{i}. {fb_txt}{' | reference: ' + msg if msg else ''}")
                                elif msg:
                                    parts.append(f"{i}. Avoid issues like: {msg}")
                            if parts:
                                guidance = "\n".join(parts)
                                guided_query = (
                                    f"{query}\n\nUser feedback to consider in this chat (address these concerns explicitly and avoid repeating mistakes):\n{guidance}"
                                )
                        break
        except Exception:
            # Non-fatal; proceed without guidance
            guided_query = query

        # Inject attachment context if available
        try:
            if chat_id:
                actx = _get_attachment_snippets(chat_id, attachment_ids, limit=3)
                if actx:
                    guided_query = f"{actx}\n\n{guided_query}"
        except Exception as _e:
            pass

        # Route to universal researcher
        routed = route_query(guided_query, history)

        # Summarize
        summary = summarize_output(routed)

        # Get critic feedback
        critic_result = provide_feedback(summary, query)
        feedback = critic_result.get("feedback", "")

        # Update in-memory conversation history
        if session_id not in conversations:
            conversations[session_id] = []
        conversations[session_id].append({"user": query, "bot": summary})

        # Keep only last 10 exchanges
        if len(conversations[session_id]) > 10:
            conversations[session_id] = conversations[session_id][-10:]

        # Persist to database
        try:
            db.add_conversation(query, summary)
        except Exception as db_err:
            logger.error(f"Failed to persist conversation: {db_err}")

        # Persist to chats JSON if chat_id is provided (or create a new one implicitly)
        try:
            chats = _load_chats()
            target = None
            if chat_id:
                for c in chats:
                    if c.get("id") == chat_id:
                        target = c
                        break
            if not target:
                # If chat_id missing or not found, create a new chat
                new_id = str(uuid.uuid4())
                now = datetime.datetime.utcnow().isoformat()
                target = {"id": new_id, "title": "New Chat", "createdAt": now, "messages": [], "feedback": []}
                chats.insert(0, target)
                chat_id = new_id
            # Ensure keys
            target.setdefault("messages", [])
            target.setdefault("feedback", [])
            # Append messages (store original query)
            target["messages"].append({"role": "user", "content": query})
            target["messages"].append({"role": "assistant", "content": summary})
            # Auto-title if still default
            title = (target.get("title") or "").strip()
            if title.lower() in ("new chat", "", "untitled") and len(target["messages"]) >= 2:
                new_title = _generate_chat_title(query, summary)
                if new_title:
                    target["title"] = new_title
            _save_chats(chats)
        except Exception as e:
            logger.error(f"Error updating chats store: {e}")

        logger.info("Query handled successfully")
        return JSONResponse({"summary": summary, "feedback": feedback, "chat_id": chat_id})

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
        # Accept both old and new payload shapes
        rating = data.get("rating")
        feedback_text = data.get("feedback", "")
        message = data.get("message") or data.get("response", "")
        query = data.get("query", "")
        chat_id = data.get("chat_id")

        success = save_feedback(feedback_text, query, message)

        # Also persist into chats JSON for per-chat learning context
        try:
            if chat_id:
                chats = _load_chats()
                for c in chats:
                    if c.get("id") == chat_id:
                        fb_list = c.setdefault("feedback", [])
                        fb_list.append({
                            "rating": rating or "",
                            "feedback": feedback_text,
                            "message": message,
                            "createdAt": datetime.datetime.utcnow().isoformat(),
                        })
                        _save_chats(chats)
                        break
        except Exception as e:
            logger.error(f"Failed to persist feedback to chat store: {e}")

        if success:
            return JSONResponse({"status": "success"})
        else:
            return JSONResponse({"status": "error"}, status_code=500)

    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return JSONResponse({"status": "error"}, status_code=500)


@app.get("/api/history")
async def get_history():
    try:
        records = db.get_history(limit=20)
        history = [
            {
                "id": r.id,
                "user_query": r.user_query,
                "bot_response": r.bot_response,
                "timestamp": r.timestamp.isoformat() if getattr(r, "timestamp", None) else None,
            }
            for r in records
        ][::-1]
        return JSONResponse({"history": history}, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return JSONResponse({"history": []}, status_code=500)


@app.delete("/api/history/{item_id}")
async def delete_history_item(item_id: int):
    try:
        ok = db.delete_conversation(item_id)
        status = 200 if ok else 404
        return JSONResponse({"deleted": ok}, status_code=status, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    except Exception as e:
        logger.error(f"Error deleting history item {item_id}: {e}")
        return JSONResponse({"deleted": False}, status_code=500)


@app.delete("/api/history")
async def clear_history():
    try:
        count = db.clear_history()
        return JSONResponse({"cleared": True, "count": count}, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return JSONResponse({"cleared": False, "count": 0}, status_code=500)


@app.post("/resummarize")
async def resummarize(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "").strip()
        session_id = data.get("session_id", "default")
        chat_id = data.get("chat_id")
        if not query:
            return JSONResponse({"summary": "", "feedback": "Empty query"}, status_code=400)

        # Try to find the most recent bot response for this query from DB
        base_response = None
        try:
            records = db.get_history(limit=50)
            for r in records:
                if (r.user_query or "").strip() == query:
                    base_response = r.bot_response
                    break
        except Exception as db_err:
            logger.error(f"Failed loading history for resummarize: {db_err}")

        # Fallback to in-memory conversation
        if not base_response:
            history = conversations.get(session_id, [])
            for h in reversed(history):
                if h.get("user") == query:
                    base_response = h.get("bot")
                    break

        if not base_response:
            return JSONResponse({"summary": "", "feedback": "No prior response found to resummarize."}, status_code=404)

        # Build guidance from recent dislikes for this chat
        guidance = None
        try:
            if chat_id:
                chats = _load_chats()
                for c in chats:
                    if c.get("id") == chat_id:
                        fbs = list(reversed(c.get("feedback", [])))[:5]
                        dislikes = [f for f in fbs if (f.get("rating") == "dislike")]
                        if dislikes:
                            parts = []
                            for i, f in enumerate(dislikes[:3], 1):
                                fb_txt = (f.get("feedback") or "").strip()
                                msg = (f.get("message") or "").strip()
                                if msg:
                                    msg = (msg[:220] + "…") if len(msg) > 220 else msg
                                if fb_txt:
                                    parts.append(f"{i}. {fb_txt}{' | reference: ' + msg if msg else ''}")
                                elif msg:
                                    parts.append(f"{i}. Avoid issues like: {msg}")
                            if parts:
                                guidance = "\n".join(parts)
                        break
        except Exception:
            guidance = None

        # Re-run summarizer on the last response with resummarize flag and optional guidance
        payload = {"response": base_response, "resummarize": True}
        if guidance:
            payload["feedback_guidance"] = guidance
            payload["query"] = query
        summary = summarize_output(payload)
        critic_result = provide_feedback(summary, query)
        feedback = critic_result.get("feedback", "")

        # Persist as a new conversation entry
        try:
            db.add_conversation(query, summary)
        except Exception as db_err:
            logger.error(f"Failed to persist resummarized conversation: {db_err}")

        # Update in-memory history as well
        conversations.setdefault(session_id, []).append({"user": query, "bot": summary})
        if len(conversations[session_id]) > 10:
            conversations[session_id] = conversations[session_id][-10:]

        return JSONResponse({"summary": summary, "feedback": feedback})

    except Exception as e:
        logger.error(f"Error in /resummarize: {e}")
        return JSONResponse({"summary": "", "feedback": "Error while resummarizing"}, status_code=500)


@app.post("/reresearch")
async def reresearch(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "").strip()
        session_id = data.get("session_id", "default")
        chat_id = data.get("chat_id")
        if not query:
            return JSONResponse({"summary": "", "feedback": "Empty query"}, status_code=400)

        history = conversations.get(session_id, [])

        # Build guided query from recent dislikes
        guided_query = query
        try:
            if chat_id:
                chats = _load_chats()
                for c in chats:
                    if c.get("id") == chat_id:
                        fbs = list(reversed(c.get("feedback", [])))[:5]
                        dislikes = [f for f in fbs if (f.get("rating") == "dislike")]
                        if dislikes:
                            parts = []
                            for i, f in enumerate(dislikes[:3], 1):
                                fb_txt = (f.get("feedback") or "").strip()
                                msg = (f.get("message") or "").strip()
                                if msg:
                                    msg = (msg[:220] + "…") if len(msg) > 220 else msg
                                if fb_txt:
                                    parts.append(f"{i}. {fb_txt}{' | reference: ' + msg if msg else ''}")
                                elif msg:
                                    parts.append(f"{i}. Avoid issues like: {msg}")
                            if parts:
                                guidance = "\n".join(parts)
                                guided_query = (
                                    f"{query}\n\nUser feedback to consider in this chat (address these concerns explicitly and avoid repeating mistakes):\n{guidance}"
                                )
                        break
        except Exception:
            guided_query = query

        # Re-run the full pipeline to generate a fresh answer
        routed = route_query(guided_query, history)
        # Mark as resummarize to encourage alternate phrasing/style in summarizer
        try:
            routed["resummarize"] = True
        except Exception:
            pass
        summary = summarize_output(routed)
        critic_result = provide_feedback(summary, query)
        feedback = critic_result.get("feedback", "")

        # Persist
        try:
            db.add_conversation(query, summary)
        except Exception as db_err:
            logger.error(f"Failed to persist reresearch conversation: {db_err}")

        # Update in-memory history
        conversations.setdefault(session_id, []).append({"user": query, "bot": summary})
        if len(conversations[session_id]) > 10:
            conversations[session_id] = conversations[session_id][-10:]

        return JSONResponse({"summary": summary, "feedback": feedback})

    except Exception as e:
        logger.error(f"Error in /reresearch: {e}")
        return JSONResponse({"summary": "", "feedback": "Error while re-researching"}, status_code=500)


# ----- Chat sidebar API (JSON store) -----
@app.get("/api/chats")
async def list_chats():
    try:
        chats = _load_chats()
        # Return only summaries
        summaries = [
            {"id": c.get("id"), "title": c.get("title", "Untitled"), "createdAt": c.get("createdAt")}
            for c in chats
        ]
        return JSONResponse(summaries)
    except Exception as e:
        logger.error(f"Error listing chats: {e}")
        return JSONResponse([], status_code=500)


@app.get("/api/chat/{chat_id}")
async def get_chat(chat_id: str):
    try:
        chats = _load_chats()
        for c in chats:
            if c.get("id") == chat_id:
                return JSONResponse({
                    "id": c.get("id"),
                    "title": c.get("title", "Untitled"),
                    "createdAt": c.get("createdAt"),
                    "messages": c.get("messages", []),
                })
        return JSONResponse({"detail": "Not found"}, status_code=404)
    except Exception as e:
        logger.error(f"Error getting chat {chat_id}: {e}")
        return JSONResponse({"detail": "Server error"}, status_code=500)


@app.post("/api/chat/new")
async def new_chat():
    try:
        chats = _load_chats()
        new_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()
        chat = {
            "id": new_id,
            "title": "New Chat",
            "createdAt": now,
            "messages": [],
        }
        chats.insert(0, chat)
        _save_chats(chats)
        return JSONResponse(chat)
    except Exception as e:
        logger.error(f"Error creating new chat: {e}")
        return JSONResponse({"detail": "Server error"}, status_code=500)


@app.delete("/api/chat/{chat_id}")
async def delete_chat(chat_id: str):
    try:
        chats = _load_chats()
        before = len(chats)
        chats = [c for c in chats if c.get("id") != chat_id]
        deleted = len(chats) < before
        if deleted:
            _save_chats(chats)
            # Purge attachments in GridFS for this chat
            try:
                if attachments_col is not None and fs is not None:
                    from bson import ObjectId
                    cur = attachments_col.find({"chat_id": chat_id}, {"_id": 1})
                    ids = [doc["_id"] for doc in cur]
                    for oid in ids:
                        try:
                            fs.delete(ObjectId(str(oid)))
                        except Exception:
                            try:
                                fs.delete(oid)
                            except Exception:
                                pass
                    attachments_col.delete_many({"chat_id": chat_id})
            except Exception as e:
                logger.error(f"Failed purging attachments for chat {chat_id}: {e}")
        return JSONResponse({"deleted": deleted}, status_code=(200 if deleted else 404), headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}")
        return JSONResponse({"deleted": False}, status_code=500)


# ----- Attachments API (defined after app init) -----
@app.post("/api/upload")
async def upload_files(chat_id: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        if fs is None:
            return JSONResponse({"detail": "Attachments storage not configured"}, status_code=500)
        results = []
        for up in files:
            meta = _store_gridfs_and_ocr(up, chat_id)
            results.append(meta)
        return JSONResponse({"attachments": results})
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return JSONResponse({"detail": "Upload failed"}, status_code=500)


@app.get("/api/attachment/{file_id}")
async def get_attachment(file_id: str):
    try:
        if fs is None:
            return JSONResponse({"detail": "Attachments storage not configured"}, status_code=500)
        from bson import ObjectId
        oid = ObjectId(file_id)
        gf = fs.get(oid)
        ct = getattr(gf, 'content_type', None) or _safe_mime(gf.filename)
        return StreamingResponse(iter(lambda: gf.read(8192), b''), media_type=ct, headers={
            'Content-Disposition': f'inline; filename="{gf.filename}"'
        })
    except Exception as e:
        logger.error(f"Download failed for {file_id}: {e}")
        return JSONResponse({"detail": "Not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
