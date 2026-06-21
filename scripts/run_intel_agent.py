"""scripts/run_intel_agent.py — standalone trigger for the Regulatory Intelligence Agent.

Usage:
    python scripts/run_intel_agent.py            # runs for all supported regulators
    python scripts/run_intel_agent.py fssai      # runs for a single regulator
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.regulatory_intel_agent import RegulatoryIntelAgent


def main():
    regulator = sys.argv[1] if len(sys.argv) > 1 else None
    agent = RegulatoryIntelAgent()
    print(f"Running Regulatory Intelligence Agent (regulator={regulator or 'all'})...")
    changes = agent.run(regulator=regulator)

    if not changes:
        print("No regulatory changes detected.")
        return

    for c in changes:
        print(f"\n--- {c.regulator.upper()} change detected ---")
        print(f"Source: {c.source_url}")
        print(f"Summary: {c.change_summary}")
        print(f"Affected categories: {c.affected_product_categories}")
        print(f"Affected ingredients: {c.affected_ingredients}")


if __name__ == "__main__":
    main()
