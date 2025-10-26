def classify_topic(query):
    if "bill" in query.lower() or "invoice" in query.lower() or "refund" in query.lower():
        return "billing"
    elif "error" in query.lower() or "issue" in query.lower() or "bug" in query.lower():
        return "technical"
    elif "feature" in query.lower() or "spec" in query.lower() or "product" in query.lower():
        return "product"
    return "general"
