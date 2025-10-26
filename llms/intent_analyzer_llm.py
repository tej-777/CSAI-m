def analyze_intent(query):
    if "how" in query.lower() or "help" in query.lower():
        return "information"
    elif "complaint" in query.lower() or "not working" in query.lower():
        return "issue"
    elif "buy" in query.lower() or "purchase" in query.lower():
        return "purchase"
    return "general"
