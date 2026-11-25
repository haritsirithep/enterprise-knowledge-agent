"""List the Gemini models your API key can use for text generation.

  python scripts/list_gemini_models.py
"""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
key = os.getenv("GEMINI_API_KEY")
if not key:
    sys.exit("GEMINI_API_KEY is not set. Add it to .env first.")

response = httpx.get(
    "https://generativelanguage.googleapis.com/v1beta/models",
    params={"pageSize": 1000},
    headers={"x-goog-api-key": key},
)
response.raise_for_status()
for m in response.json().get("models", []):
    if "generateContent" in m.get("supportedGenerationMethods", []):
        print(f"gemini/{m['name'].removeprefix('models/')}")
