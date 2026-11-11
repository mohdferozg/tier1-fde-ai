import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# List available models, filter for text generation
print("Models available for generateContent:")
print("-" * 60)
for model in client.models.list():
    # The list includes embedding, image, etc. Filter for chat models.
    name = model.name
    if any(k in name.lower() for k in ["gemini", "flash", "pro"]):
        print(name)