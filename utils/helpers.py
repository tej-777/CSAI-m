import re

def sanitize_text(text):
    # Removes unwanted characters from user input
    return re.sub(r'[^\w\s\.,!?-]', '', text)

def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def extract_keywords(text):
    keywords = re.findall(r'\b\w+\b', text.lower())
    return list(set(keywords))

def format_response(text):
    return text.strip().capitalize()
