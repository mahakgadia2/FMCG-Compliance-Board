# RegulAI — Multi-Agent Regulatory Review Board

FMCG brands in India must comply with multiple regulatory bodies simultaneously.
RegulAI automates this review using a multi-agent system: one specialist agent
per regulator, an orchestrator that routes work, a conflict detector that
catches contradictions between regulators, and a synthesizer that produces a
final compliance report — just like a real review board.

## Architecture

```
[Streamlit UI] → [AnalysisPipeline]
                     ├─ OrchestratorAgent      (classifies applicable regulators)
                     ├─ ExpertAgent(fssai)  ─┐
                     ├─ ExpertAgent(ayush)  ─┤ run concurrently (asyncio.gather)
                     │        ↓ RAG: ChromaDB (regulator-namespaced collections)
                     ├─ ConflictDetectorAgent (pairwise contradiction check)
                     └─ ReportSynthesizerAgent (final JSON + summary)

[RegulatoryIntelAgent]  (independent, triggered from the sidebar)
   └─ crawls regulator sites → chunks → embeds → ChromaDB
```

Every agent inherits from `BaseAgent`, reads/writes a shared `AnalysisContext`,
and never returns a value directly — all state flows through the context
object, which also accumulates a timestamped log shown live in the UI.

## Setup

### 1. Environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your Gemini key

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY=your_key_here
```

> **No key? No problem.** Every LLM call has a rule-based or deterministic
> fallback (see `OrchestratorAgent._rule_based_fallback`, `ExpertAgent._fallback_verdict`,
> `Embedder._fallback_embed`), so the pipeline still runs end-to-end offline —
> useful for hackathon demo reliability, just with lower-quality verdicts.

### 3. Seed the database

```bash
python scripts/seed_db.py
```

Expected output:
```
[FSSAI] Ingesting labeling_regulations.txt ... N chunks added
[FSSAI] Ingesting health_claims.txt ... N chunks added
[FSSAI] Ingesting additives_list.txt ... N chunks added
[AYUSH] Ingesting herbal_guidelines.txt ... N chunks added
[AYUSH] Ingesting permissible_ingredients.txt ... N chunks added
[AYUSH] Ingesting claim_restrictions.txt ... N chunks added
✓ ChromaDB seeded. Total: N chunks across 2 collections.
```

### 4. Run the app

```bash
streamlit run app.py
```

### 5. Try the demo

In the UI, pick a demo product from the dropdown (e.g. **"Kids' Ashwagandha
Gummies"** — deliberately designed to trigger both an FSSAI disease-claim
violation and an AYUSH dosage-cap violation) and click **Analyze**.

## Project layout

See the full annotated tree in the spec; key entry points:

- `app.py` — Streamlit UI
- `core/pipeline.py` — wires all agents together
- `agents/` — one file per agent
- `rag/` — ChromaDB ingestion/retrieval/embedding
- `models/` — all dataclasses (ProductSpec, Verdict, Conflict, FinalReport, RegulationChunk)
- `scripts/seed_db.py` — one-time seed ingestion
- `scripts/run_intel_agent.py` — standalone trigger for the crawler agent
- `tests/test_pipeline.py` — end-to-end smoke test

## Stretch features included / scaffolded

- ✅ Regulatory Intelligence Agent (`agents/regulatory_intel_agent.py`) — live
  crawl + change detection + ChromaDB re-ingestion, triggerable from the sidebar.
- ✅ Confidence display per verdict in the UI.
- ✅ Historical report storage — every report is saved to `data/reports/<id>.json`.
- ✅ Conflict resolution suggestions — `suggested_resolution` field, populated by Gemini.
- ⏳ BIS / CDSCO expert agents — not wired in (MVP scope is FSSAI + AYUSH per
  the approved spec); add to `config.SUPPORTED_REGULATORS` and drop in
  `prompts/expert_bis.txt` / `expert_cdsco.txt` to extend.
- ⏳ Streaming token-by-token report rendering — not implemented; the UI
  renders once the pipeline completes.
