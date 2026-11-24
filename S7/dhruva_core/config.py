import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ADK reads GOOGLE_API_KEY. If you set GEMINI_API_KEY in S1, reuse it.
if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

# A free key allows few requests a day on gemini-2.5-flash (20 on the key we tested), so default to the lite model.
MODEL = os.environ.get("DHRUVA_MODEL", "gemini-flash-lite-latest")
HERE = Path(__file__).parent
CRITERIA = ["stage", "sector", "geography", "founder_profile", "business_model", "round_size"]
ADVANCE_AT = 7.0
MIN_EVIDENCE = 3
