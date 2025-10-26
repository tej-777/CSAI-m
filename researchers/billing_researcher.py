def handle_billing_query(query):
    # Dummy logic – integrate with real billing systems or pass through LLM
    if "refund" in query.lower():
        response = "Your refund will be processed within 5 business days."
    else:
        response = "For billing support, please provide your invoice number."
    return {"response": response, "topic": "billing"}
