"""Compute deterministic capability coverage for eval tool ablations."""

import json
from pathlib import Path

DATASET = Path(__file__).parents[1] / "evals" / "cases.json"
CONFIGURATIONS = {
    "no_tools": set(),
    "sql_only": {"financial_overview"},
    "rag_only": {"knowledge_search"},
    "sql_and_rag": {"financial_overview", "knowledge_search"},
}


def coverage(cases: list[dict[str, object]], tools: set[str]) -> float:
    supported = 0
    for case in cases:
        expected = set(case["expected_tools"])
        if case["expect_unsupported"] or expected.issubset(tools):
            supported += 1
    return supported / len(cases)


def main() -> None:
    cases = json.loads(DATASET.read_text())
    for name, tools in CONFIGURATIONS.items():
        print(f"{name}: {coverage(cases, tools):.0%}")


if __name__ == "__main__":
    main()
