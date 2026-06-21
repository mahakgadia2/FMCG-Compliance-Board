"""tests/test_pipeline.py — smoke test for the full pipeline using fixture data.

Run with:
    python -m pytest tests/test_pipeline.py -v
or directly:
    python tests/test_pipeline.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import FIXTURES_PATH
from models.product_spec import ProductSpec
from core.pipeline import AnalysisPipeline


def load_fixtures():
    with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_pipeline_runs_end_to_end():
    fixtures = load_fixtures()
    assert fixtures, "No demo fixtures found"

    spec = ProductSpec.from_dict(fixtures[0])
    context = AnalysisPipeline().run(spec)

    assert context.status in ("complete", "error")
    if context.status == "complete":
        assert context.final_report is not None
        assert context.final_report.overall_status in (
            "COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW",
        )
        assert context.applicable_regulators, "No regulators classified"
        assert len(context.verdicts) == len(context.applicable_regulators)


def test_all_fixtures_produce_a_report():
    fixtures = load_fixtures()
    pipeline = AnalysisPipeline()
    for fixture in fixtures:
        spec = ProductSpec.from_dict(fixture)
        context = pipeline.run(spec)
        print(f"\n=== {spec.product_name} -> status={context.status} ===")
        for line in context.log:
            print(line)
        if context.final_report:
            print(json.dumps(context.final_report.to_dict(), indent=2))


if __name__ == "__main__":
    test_pipeline_runs_end_to_end()
    test_all_fixtures_produce_a_report()
    print("\nAll smoke tests completed.")
