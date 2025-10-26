def handle_tech_query(query):
    # Dummy logic – integrate with knowledge base or LLM
    if "error" in query.lower():
        response = "Please restart your device and try again. If the issue persists, contact support."
    else:
        response = "For technical issues, can you specify the error code or software version?"
    return {"response": response, "topic": "technical"}
