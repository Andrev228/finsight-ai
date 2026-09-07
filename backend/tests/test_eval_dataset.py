"""Contract tests for the live evaluation dataset."""

import json
from pathlib import Path


def test_eval_dataset_has_unique_valid_cases():
    path = Path(__file__).parents[1] / "evals" / "cases.json"
    cases = json.loads(path.read_text())

    assert len(cases) >= 4
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["question"].strip()
        assert set(case["expected_tools"]) <= {
            "financial_overview",
            "knowledge_search",
        }
        assert isinstance(case["expect_unsupported"], bool)
        assert isinstance(case["require_analytics"], bool)
        assert isinstance(case["min_sources"], int)
