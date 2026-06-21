"""core/prompt_loader.py — loads .txt prompt templates from prompts/."""
from config import PROMPTS_DIR


def load_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")
