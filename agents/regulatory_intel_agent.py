"""agents/regulatory_intel_agent.py — background/on-demand crawler + ingestion agent.

Runs independently from the analysis pipeline (does NOT take an AnalysisContext).
Can be triggered manually via the Streamlit sidebar or scripts/run_intel_agent.py.
"""
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from agents.llm_client import GeminiClient, GeminiUnavailable
from rag.retriever import Retriever
from rag.ingestion import Ingestion
from rag.embedder import Embedder
from models.regulation import RegulatoryChange


class RegulatoryIntelAgent:
    REGULATOR_SOURCES: Dict[str, List[str]] = {
        "fssai": [
            "https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php",
        ],
        "ayush": [
            "https://main.ayush.gov.in/regulation",
        ],
    }

    def __init__(self):
        self.retriever = Retriever()
        self.ingestion = Ingestion()
        self.embedder = Embedder()
        self.llm = GeminiClient()
        # In-memory hash cache; a real deployment would persist this in
        # ChromaDB metadata or a small sidecar table.
        self._content_hashes: Dict[str, str] = {}

    def run(self, regulator: Optional[str] = None) -> List[RegulatoryChange]:
        """
        Main entry point. If regulator is None, runs for all supported regulators.
        Returns list of detected RegulatoryChange objects.
        """
        regulators = [regulator] if regulator else list(self.REGULATOR_SOURCES.keys())
        changes: List[RegulatoryChange] = []

        for reg in regulators:
            for url in self.REGULATOR_SOURCES.get(reg, []):
                text = self._fetch_page(url)
                if not text:
                    continue
                if self._detect_new_content(reg, text):
                    old_text = self._content_hashes.get(f"{reg}:{url}:text", "")
                    summary = self._summarize_change(old_text, text)
                    affected = self._identify_affected_products(summary)
                    change = RegulatoryChange(
                        change_id=str(uuid.uuid4()),
                        regulator=reg,
                        detected_at=datetime.now().isoformat(),
                        source_url=url,
                        document_title=url.split("/")[-1] or url,
                        change_summary=summary,
                        affected_product_categories=affected.get("categories", []),
                        affected_ingredients=affected.get("ingredients", []),
                        severity="INFORMATIONAL",
                        raw_text=text[:5000],
                        is_acknowledged=False,
                    )
                    changes.append(change)
                    self._ingest_new_chunks(reg, text, url)

        return changes

    def _fetch_page(self, url: str) -> str:
        """Fetch and clean HTML -> plain text. Returns empty string on failure."""
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Manthan/1.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            return soup.get_text(separator="\n", strip=True)
        except Exception:
            return ""

    def _detect_new_content(self, regulator: str, fetched_text: str) -> bool:
        """Compare fetched_text hash against the cached hash for this source."""
        key = f"{regulator}:hash"
        new_hash = hashlib.sha256(fetched_text.encode("utf-8")).hexdigest()
        old_hash = self._content_hashes.get(key)
        self._content_hashes[key] = new_hash
        self._content_hashes[f"{regulator}:text"] = fetched_text
        return old_hash is not None and old_hash != new_hash or old_hash is None

    def _summarize_change(self, old_text: str, new_text: str) -> str:
        """Gemini call: 'What changed between these two versions of the regulation?'"""
        from core.prompt_loader import load_prompt
        prompt = load_prompt("regulatory_intel.txt").format(
            old_text=old_text[:3000] or "(no prior version on record)",
            new_text=new_text[:3000],
        )
        try:
            return self.llm.generate(prompt).strip()
        except GeminiUnavailable:
            return "New or updated regulatory content detected (Gemini unavailable for detailed summary)."

    def _identify_affected_products(self, change_summary: str) -> Dict[str, List[str]]:
        """
        Gemini call: given this change summary, which product categories
        and ingredients might be affected? Returns {"categories": [...], "ingredients": [...]}
        """
        prompt = (
            "Given this regulatory change summary, list affected product "
            "categories and ingredients as JSON only: "
            '{"categories": [...], "ingredients": [...]}\n\n'
            f"Change summary: {change_summary}"
        )
        try:
            return self.llm.parse_json(self.llm.generate(prompt))
        except Exception:
            return {"categories": [], "ingredients": []}

    def _ingest_new_chunks(self, regulator: str, text: str, source_url: str) -> None:
        """Chunk, embed, and upsert into ChromaDB under the regulator's namespace."""
        self.ingestion.ingest_text(
            text=text,
            regulator=regulator,
            document_title=source_url.split("/")[-1] or source_url,
            source_url=source_url,
        )
