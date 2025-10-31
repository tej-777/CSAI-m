import os
from dotenv import load_dotenv

# Load variables from a local .env file if present
load_dotenv()


class Settings:
    PORT = int(os.getenv("PORT", 8000))

    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    LANGGRAPH_API_KEY = os.getenv("LANGGRAPH_API_KEY", "")

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///supportai.db")
    FEEDBACK_STORE = "feedback_data.json"
    DEBUG = True

    # MongoDB (GridFS) for attachments
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "CSAI")

    # Client API settings
    API_BASE_URL = os.getenv("API_BASE_URL", f"http://localhost:{PORT}")
    REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", 10))
    REQUEST_RETRY_TOTAL = int(os.getenv("REQUEST_RETRY_TOTAL", 3))
    REQUEST_RETRY_BACKOFF_FACTOR = float(
        os.getenv("REQUEST_RETRY_BACKOFF_FACTOR", 0.5))
    REQUEST_RETRY_STATUS_FORCELIST = tuple(
        int(code.strip()) for code in os.getenv("REQUEST_RETRY_STATUS_FORCELIST", "429,500,502,503,504").split(",")
        if code.strip().isdigit()
    )


settings = Settings()
