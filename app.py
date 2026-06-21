"""app.py — Streamlit demo UI for RegulAI.

Run with:
    streamlit run app.py
"""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import FIXTURES_PATH, REPORTS_DIR, SUPPORTED_REGULATORS
from models.product_spec import ProductSpec
from core.pipeline import AnalysisPipeline
from agents.regulatory_intel_agent import RegulatoryIntelAgent
from rag.retriever import Retriever

st.set_page_config(page_title="RegulAI — Regulatory Review Board", page_icon="🛡️", layout="wide")

STATUS_COLORS = {
    "COMPLIANT": "🟢",
    "NON_COMPLIANT": "🔴",
    "NEEDS_REVIEW": "🟡",
    "NOT_APPLICABLE": "⚪",
}

SEVERITY_COLORS = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}


def load_demo_products():
    if not FIXTURES_PATH.exists():
        return []
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def render_report(report):
    badge = STATUS_COLORS.get(report.overall_status, "⚪")
    st.markdown(f"## {badge} Overall Status: **{report.overall_status}**")
    st.markdown(f"**Product:** {report.product_name}")
    st.markdown(f"**Applicable Regulators:** {', '.join(r.upper() for r in report.applicable_regulators)}")
    st.markdown(f"**Summary:** {report.summary}")

    st.markdown("### Per-Regulator Verdicts")
    cols = st.columns(len(report.verdicts) or 1)
    for col, verdict in zip(cols, report.verdicts):
        with col:
            vbadge = STATUS_COLORS.get(verdict.status, "⚪")
            st.markdown(f"#### {vbadge} {verdict.regulator.upper()}")
            st.markdown(f"**Status:** {verdict.status}")
            st.markdown(f"**Confidence:** {verdict.confidence:.0%}")
            st.markdown(f"_{verdict.reasoning}_")
            if verdict.issues:
                st.markdown("**Issues:**")
                for issue in verdict.issues:
                    sev = SEVERITY_COLORS.get(issue.severity, "⚪")
                    st.markdown(f"- {sev} **{issue.attribute}**: {issue.description}")
                    if issue.regulation_reference:
                        st.caption(issue.regulation_reference)
            else:
                st.markdown("_No issues found._")

    st.markdown("### Conflicts")
    if report.conflicts:
        for c in report.conflicts:
            sev = SEVERITY_COLORS.get(c.severity, "⚪")
            st.markdown(
                f"{sev} **{c.attribute}** — {c.regulator_a.upper()} vs {c.regulator_b.upper()}: {c.description}"
            )
            if c.suggested_resolution:
                st.caption(f"Suggested resolution: {c.suggested_resolution}")
    else:
        st.markdown("_No conflicts detected._")

    st.markdown("### Action Items")
    if report.action_items:
        for item in report.action_items:
            st.markdown(f"- {item}")
    else:
        st.markdown("_No action items._")


def main():
    st.title("🛡️ RegulAI — Multi-Agent Regulatory Review Board")
    st.caption(
        "FMCG brands in India must comply with multiple regulatory bodies at once. "
        "RegulAI automates the review using a specialist agent per regulator."
    )

    # --- Sidebar: Regulatory Intelligence Agent controls ---
    with st.sidebar:
        st.header("📡 Regulatory Intelligence")
        try:
            stats = Retriever().get_collection_stats()
            for reg, count in stats.items():
                st.metric(label=reg.upper(), value=f"{count} chunks")
        except Exception as e:
            st.warning(f"Could not load ChromaDB stats: {e}")

        if st.button("🔄 Sync Regulations"):
            with st.spinner("Crawling regulator sites..."):
                try:
                    agent = RegulatoryIntelAgent()
                    changes = agent.run()
                    if changes:
                        st.success(f"Detected {len(changes)} change(s).")
                        for c in changes:
                            st.write(f"**{c.regulator.upper()}**: {c.change_summary}")
                    else:
                        st.info("No new regulatory changes detected.")
                except Exception as e:
                    st.error(f"Sync failed: {e}")

        st.divider()
        st.caption("Run `python scripts/seed_db.py` once before first use to load seed regulations.")

    # --- Main: product input form ---
    st.header("1️⃣ Product Specification")

    demo_products = load_demo_products()
    demo_names = [p["product_name"] for p in demo_products]
    chosen_demo = st.selectbox("Load a demo product (optional)", ["— None —"] + demo_names)

    defaults = {}
    if chosen_demo != "— None —":
        defaults = next(p for p in demo_products if p["product_name"] == chosen_demo)

    with st.form("product_form"):
        c1, c2 = st.columns(2)
        with c1:
            product_name = st.text_input("Product Name", value=defaults.get("product_name", ""))
            category = st.selectbox(
                "Category",
                ["packaged_food", "herbal_supplement", "functional_food"],
                index=["packaged_food", "herbal_supplement", "functional_food"].index(
                    defaults.get("category", "packaged_food")
                ) if defaults.get("category") in ["packaged_food", "herbal_supplement", "functional_food"] else 0,
            )
            ingredients = st.text_area(
                "Ingredients (one per line)",
                value="\n".join(defaults.get("ingredients", [])),
            )
            claims = st.text_area(
                "Claims (one per line)",
                value="\n".join(defaults.get("claims", [])),
            )
        with c2:
            target_demographic = st.selectbox(
                "Target Demographic",
                ["adults", "children", "elderly"],
                index=["adults", "children", "elderly"].index(defaults.get("target_demographic", "adults"))
                if defaults.get("target_demographic") in ["adults", "children", "elderly"] else 0,
            )
            net_weight_grams = st.number_input(
                "Net Weight (grams)", value=float(defaults.get("net_weight_grams", 50.0)), min_value=0.0
            )
            is_imported = st.checkbox("Is Imported?", value=defaults.get("is_imported", False))
            packaging_material = st.text_input(
                "Packaging Material", value=defaults.get("packaging_material", "")
            )
            country_of_origin = st.text_input(
                "Country of Origin", value=defaults.get("country_of_origin", "India")
            )
            has_herbal_ingredients = st.checkbox(
                "Has Herbal Ingredients?", value=defaults.get("has_herbal_ingredients", False)
            )
            has_health_claims = st.checkbox(
                "Has Health Claims?", value=defaults.get("has_health_claims", False)
            )

        submitted = st.form_submit_button("🔍 Analyze")

    if submitted:
        spec = ProductSpec(
            product_name=product_name,
            category=category,
            ingredients=[i.strip() for i in ingredients.splitlines() if i.strip()],
            claims=[c.strip() for c in claims.splitlines() if c.strip()],
            target_demographic=target_demographic,
            net_weight_grams=net_weight_grams,
            is_imported=is_imported,
            packaging_material=packaging_material,
            country_of_origin=country_of_origin,
            has_herbal_ingredients=has_herbal_ingredients,
            has_health_claims=has_health_claims,
        )

        st.header("2️⃣ Agent Pipeline")
        log_placeholder = st.empty()

        with st.spinner("Running multi-agent analysis..."):
            pipeline = AnalysisPipeline()
            context = pipeline.run(spec)

        log_placeholder.code("\n".join(context.log), language=None)

        st.header("3️⃣ Final Report")
        if context.final_report:
            render_report(context.final_report)

            report_path = REPORTS_DIR / f"{context.final_report.report_id}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(context.final_report.to_dict(), f, indent=2)
            st.caption(f"Report saved to {report_path}")
        else:
            st.error(f"Pipeline did not complete. Status: {context.status}. Error: {context.error}")


if __name__ == "__main__":
    main()
