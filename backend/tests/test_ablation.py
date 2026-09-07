"""Deterministic capability ablation tests."""

import json

from app.ai.schemas import ALLOWED_TOOLS
from scripts.run_ablation import CONFIGURATIONS, DATASET, coverage


def test_full_toolset_covers_every_eval_capability():
    cases = json.loads(DATASET.read_text())

    assert CONFIGURATIONS["sql_and_rag"] == ALLOWED_TOOLS
    assert coverage(cases, CONFIGURATIONS["no_tools"]) == 0.25
    assert coverage(cases, CONFIGURATIONS["sql_only"]) == 0.5
    assert coverage(cases, CONFIGURATIONS["rag_only"]) == 0.5
    assert coverage(cases, CONFIGURATIONS["sql_and_rag"]) == 1.0
