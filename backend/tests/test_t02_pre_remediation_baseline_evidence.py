"""Validate the recorded T-02 result from the pre-remediation assessment."""

import json
from pathlib import Path


def test_t02_pre_remediation_baseline_was_a_failure():
    evidence_path = (
        Path(__file__).resolve().parents[2]
        / "evidence"
        / "privacy_assessment_runtime_results_2026-10-04.json"
    )
    results = json.loads(evidence_path.read_text(encoding="utf-8"))
    t02 = next(row for row in results if row["id"] == "T-02")

    assert t02["outcome"] == "FAIL"
    print(
        json.dumps(
            {
                "test": "T-02",
                "assessment_period": "pre-remediation baseline (2026-10-04)",
                "result": "FAIL",
                "observation": t02["observation"],
                "evidence": t02["evidence"],
            },
            indent=2,
        )
    )
