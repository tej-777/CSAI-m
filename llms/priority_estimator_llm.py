def estimate_priority(summary):
    text = summary.lower()
    if "refund" in text or "not working" in text or "urgent" in text:
        return "high"
    elif "feedback" in text or "feature" in text:
        return "medium"
    else:
        return "low"
