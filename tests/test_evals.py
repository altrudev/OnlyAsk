from onlyask.evals import run_evaluations


def test_evaluation_harness_has_no_expected_failures():
    report = run_evaluations()

    assert report.summary["failed_cases"] == 0
    assert report.summary["passed_cases"] == report.summary["total_cases"]
    assert report.summary["pass_rate"] == 1.0


def test_evaluation_harness_detects_no_unsafe_allows_or_unnecessary_escalations():
    report = run_evaluations()

    assert report.summary["unsafe_allows"] == 0
    assert report.summary["unnecessary_escalations"] == 0
    assert report.summary["observed_human_decisions"] == report.summary["expected_human_decisions"]


def test_evaluation_harness_preserves_ledger_integrity():
    report = run_evaluations()

    assert report.summary["all_ledgers_valid"] is True


def test_evaluation_report_covers_distinct_governance_failure_modes():
    report = run_evaluations()
    names = {case.name for case in report.cases}

    assert "stale predecessor blocks execution" in names
    assert "failed postcondition restores predecessor" in names
    assert "one-time exact grant cannot silently replay" in names
    assert "exact grant rejects parameter widening" in names
    assert "directive-bearing retrieved content remains evidence" in names
