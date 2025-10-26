def handle_product_query(query):
    # Dummy logic – connect to product DB or answer via LLM
    if "features" in query.lower():
        response = "Our product features include AI-based automation for customer support, multi-language support, and realtime analytics."
    else:
        response = "For product details, please specify the product model or name."
    return {"response": response, "topic": "product"}
