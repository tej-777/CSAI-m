import google.generativeai as genai

# Replace with your actual API key
GEMINI_API_KEY = ""

genai.configure(api_key=GEMINI_API_KEY)

print("=" * 60)
print("Available Gemini Models:")
print("=" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")

print("\n" + "=" * 60)
print("Testing a simple query with different models:")
print("=" * 60)

# List of model names to test
models_to_test = [
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
    'gemini-1.5-pro',
    'gemini-1.5-pro-latest',
    'gemini-pro'
]

for model_name in models_to_test:
    try:
        print(f"\nTesting: {model_name}")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello in one sentence")
        print(f"✓ SUCCESS: {response.text[:50]}...")
        print(f"👉 USE THIS MODEL: {model_name}")
        break  # Stop after first successful model
    except Exception as e:
        print(f"✗ FAILED: {str(e)[:100]}")

print("\n" + "=" * 60)
