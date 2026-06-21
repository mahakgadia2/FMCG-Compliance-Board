"""
config.py
All constants live here: paths, model names, regulator list.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
CHROMA_DIR = DATA_DIR / "chroma_db"
REPORTS_DIR = DATA_DIR / "reports"
PROMPTS_DIR = BASE_DIR / "prompts"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "demo_products.json"

for d in (CHROMA_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Models ---
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_EMBED_MODEL = "models/text-embedding-004"

# --- Regulators ---
# MVP scope: fssai + ayush. bis / cdsco are stretch and can be added here later.
SUPPORTED_REGULATORS = ["fssai", "ayush"]

# --- Chunking ---
CHUNK_SIZE_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 50

# --- Retrieval ---
TOP_K_CHUNKS = 5

# --- Misc ---
LLM_TIMEOUT_SECONDS = 30
LLM_MAX_RETRIES = 2