from __future__ import annotations

from pathlib import Path

import pytest

from onlyask.dogfood import DogfoodProject, DogfoodSession, SafeTestRunner
from onlyask.github_adapter import GitHubAPIError, GitHubAdapter


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.head_sha = "abc1234def5678"
        self.base_ref = "main"
        self.merged = False
        self.merge_commit_sha = ""
        self.fail_merge_transport = False
        self.merge_happens_before_transport_failure = False
        self.bad_merge_sha = False

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == "/repos/altrudev/OnlyAsk":
            return {"default_branch": "main", "visibility": "public", "archived": False, "open_issues_count": 2}
        if path == "/repos/altrudev/OnlyAsk/pulls?state=open&per_page=10":
            return [{"number": 7, "title": "Dogfood", "head": {"ref": "dogfood"}, "base": {"ref": self.base_ref}, "html_url": "https://example/pr/7"}]
        if path == "/repos/altrudev/OnlyAsk/pulls/7" and method == "GET":
            return {
                "number": 7,
                "title": "Dogfood",
                "head": {"sha": self.head_sha, "ref": "dogfood"},
                "base": {"ref": self.base_ref},
                "state": "open" if not self.merged else "closed",
                "merged": self.merged,
                "mergeable": True,
                "merge_commit_sha": self.merge_commit_sha,
                "html_url": "https://example/pr/7",
            }
        if path == "/repos/altrudev/OnlyAsk/pulls/7/merge" and method == "PUT":
            assert payload == {"sha": self.head_sha, "merge_method": "squash"}
            if self.fail_merge_transport:
                if self.merge_happens_before_transport_failure:
                    self.merged = True
                    self.merge_commit_sha = "reconciledsha"
                raise GitHubAPIError("transport failed")
            self.merged = True
            self.merge_commit_sha = "observedsha" if self.bad_merge_sha else "mergedsha"
            return {"merged": True, "sha": "returnedsha" if self.bad_merge_sha else self.merge_commit_sha}
        raise AssertionError((method, path, payload))


class FakeRunner:
    def __init__(self, tested_sha="abc1234def5678", ok=True):
        self.tested_sha = tested_sha
        self.ok = ok

    def run(self, project):
        return {
            "available": True,
            "ok": self.ok,
            "returncode": 0 if self.ok else 1,
            "command": "python -m pytest -q",
            "output": "passed" if self.ok else "failed",
            "tested_sha": self.tested_sha,
        }


def session(runner=None):
    transport = FakeTransport()
    s = DogfoodSession(
        projects=[DogfoodProject("OnlyAsk", "altrudev/OnlyAsk", "main", "/tmp")],
        github=GitHubAdapter(transport),
        runner=runner or FakeRunner(),
    )
    return s, transport


def prepare_merge(s):
    tested = s.run_tests("altrudev/OnlyAsk")
    assert tested.state.value == "verified"
    return s.request_merge("altrudev/OnlyAsk", 7)


def test_inspection_and_tests_are_automatic():
    s, _ = session()
    inspected = s.inspect("altrudev/OnlyAsk")
    tested = s.run_tests("altrudev/OnlyAsk")
    assert inspected.state.value == "verified"
    assert tested.state.value == "verified"
    assert tested.output["ok"] is True
    assert tested.output["tested_sha"] == "abc1234def5678"
    assert s.pending == {}
    assert s.kernel.ledger.verify_chain()


def test_merge_cannot_be_requested_without_passing_tests():
    s, _ = session()
    with pytest.raises(ValueError, match="must pass"):
        s.request_merge("altrudev/OnlyAsk", 7)


def test_merge_cannot_use_passing_tests_from_different_commit():
    s, _ = session(FakeRunner(tested_sha="different999999"))
    s.run_tests("altrudev/OnlyAsk")
    with pytest.raises(ValueError, match="not bound"):
        s.request_merge("altrudev/OnlyAsk", 7)


def test_merge_cannot_use_failed_test_run():
    s, _ = session(FakeRunner(ok=False))
    s.run_tests("altrudev/OnlyAsk")
    with pytest.raises(ValueError, match="must pass"):
        s.request_merge("altrudev/OnlyAsk", 7)


def test_merge_requires_human_then_uses_exact_one_time_grant_and_successor_binding():
    s, transport = session()
    requested = prepare_merge(s)
    assert requested.state.value == "escalated"
    assert requested.decision.authority_basis == "constraint:irreversible_requires_scoped_grant"
    assert transport.merged is False
    assert requested.transition_id in s.pending
    assert s.pending[requested.transition_id].detail["tested_sha"] == transport.head_sha

    approved = s.approve_once(requested.transition_id)
    assert approved.state.value == "verified"
    assert approved.verification_passed is True
    assert transport.merged is True
    assert transport.merge_commit_sha == approved.output["sha"]
    assert s.envelope.grants[-1].remaining_uses == 0
    assert s.kernel.ledger.verify_chain()


def test_merge_fails_stale_if_head_changes_after_human_review():
    s, transport = session()
    requested = prepare_merge(s)
    transport.head_sha = "changed999999"
    approved = s.approve_once(requested.transition_id)
    assert approved.state.value == "stale"
    assert transport.merged is False
    assert s.envelope.grants[-1].remaining_uses == 0
    assert s.kernel.ledger.entries[-1].event == "scoped_grant_revoked_after_attempt"


def test_merge_fails_stale_if_pr_is_retargeted_after_human_review():
    s, transport = session()
    requested = prepare_merge(s)
    transport.base_ref = "release"
    approved = s.approve_once(requested.transition_id)
    assert approved.state.value == "stale"
    assert transport.merged is False
    assert s.envelope.grants[-1].remaining_uses == 0


def test_transport_failure_is_reconciled_when_merge_successor_is_observable():
    s, transport = session()
    requested = prepare_merge(s)
    transport.fail_merge_transport = True
    transport.merge_happens_before_transport_failure = True

    approved = s.approve_once(requested.transition_id)

    assert approved.state.value == "verified"
    assert approved.output["reconciled_after_transport_error"] is True
    assert approved.output["sha"] == "reconciledsha"


def test_transport_failure_without_observable_successor_becomes_uncertain():
    s, transport = session()
    requested = prepare_merge(s)
    transport.fail_merge_transport = True

    approved = s.approve_once(requested.transition_id)

    assert approved.state.value == "uncertain"
    assert transport.merged is False
    assert s.envelope.grants[-1].remaining_uses == 0
    assert any(e.event == "irreversible_outcome_uncertain" for e in s.kernel.ledger.entries)


def test_mismatched_successor_sha_becomes_uncertain_not_fake_recovery():
    s, transport = session()
    requested = prepare_merge(s)
    transport.bad_merge_sha = True

    approved = s.approve_once(requested.transition_id)

    assert approved.state.value == "uncertain"
    assert approved.verification_passed is False
    assert approved.recovery_passed is None


def test_reject_records_human_decision():
    s, _ = session()
    requested = prepare_merge(s)
    result = s.reject(requested.transition_id)
    assert result["state"] == "rejected"
    assert not s.pending
    assert s.kernel.ledger.entries[-1].event == "human_rejected"


def test_safe_runner_binds_tests_to_git_head_and_does_not_inherit_backend_secrets(monkeypatch, tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.1'\n")
    monkeypatch.setenv("ONLYASK_GITHUB_TOKEN", "github-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "model-secret")
    seen = []

    class Done:
        def __init__(self, returncode, stdout, stderr=""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command, **kwargs):
        seen.append({"command": command, **kwargs})
        if command == ["git", "rev-parse", "HEAD"]:
            return Done(0, "abc1234def5678\n")
        return Done(0, "ok")

    monkeypatch.setattr("onlyask.dogfood.subprocess.run", fake_run)
    project = DogfoodProject("X", "a/b", local_path=str(tmp_path))
    result = SafeTestRunner().run(project)
    assert result["ok"] is True
    assert result["tested_sha"] == "abc1234def5678"
    assert seen[0]["command"] == ["git", "rev-parse", "HEAD"]
    assert seen[1]["command"][1:] == ["-m", "pytest", "-q"]
    assert all(call.get("shell") is None for call in seen)
    assert all("ONLYASK_GITHUB_TOKEN" not in call["env"] for call in seen)
    assert all("AWS_SECRET_ACCESS_KEY" not in call["env"] for call in seen)
    assert all("OPENAI_API_KEY" not in call["env"] for call in seen)
