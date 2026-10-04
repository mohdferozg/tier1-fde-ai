import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")

print("Key present:", key is not None)
print("Key length:", len(key) if key else 0)
print("Starts with 'AIza' (legacy format):", key.startswith("AIza") if key else False)
print("Starts with 'AQ.' (new format):", key.startswith("AQ.") if key else False)
print("Length is 39 (legacy) or 53 (new):", len(key) in (39, 53) if key else False)