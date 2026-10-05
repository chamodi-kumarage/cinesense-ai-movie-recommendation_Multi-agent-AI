"""Show the recorded T-04 pre-remediation failure evidence only."""

import json
from pathlib import Path


def test_t04_pre_remediation_baseline_was_a_failure():
    evidence_path = (
        Path(__file__).resolve().parents[2]
        / "evidence"
        / "privacy_assessment_runtime_results_2026-10-04.json"
    )
    results = json.loads(evidence_path.read_text(encoding="utf-8"))
    t04 = next(row for row in results if row["id"] == "T-04")

    assert t04["outcome"] == "FAIL"
    detail = {
        "result": "FAIL",
        "why_this_failed": (
            "The test required both explicit preferences and inferred conversational "
            "state to stay within the intended profile. The explicit preference "
            "endpoints were reachable for both profiles (HTTP 200/200), but that "
            "alone did not establish isolation of learned conversation state."
        ),
        "evidence_facts": [
            "Profile A and Profile B preference reads both returned HTTP 200.",
            "The inspected ConversationState schema had no profile_id column.",
            "A shared account-level ConversationState row existed for Alpha, rather "
            "than separate state ownership keyed to each profile.",
            "Therefore inferred preferences/history did not have a persisted profile "
            "boundary in the baseline implementation.",
        ],
        "impact_interpretation": (
            "This demonstrates a profile-isolation control failure for persisted "
            "conversational state. It does not by itself prove that Profile B "
            "received Profile A's preference value or that a recommendation disclosed it."
        ),
        "source_observation": t04["observation"],
        "evidence_id": t04["evidence"],
        "evidence_file": "evidence/privacy_assessment_runtime_results_2026-10-04.json",
    }
    print(
        json.dumps(
            {
                "test": "T-04",
                "assessment_period": "pre-remediation baseline (2026-10-04)",
                **detail,
            },
            indent=2,
        )
    )
