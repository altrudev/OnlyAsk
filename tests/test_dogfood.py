from __future__ import annotations

from pathlib import Path

from onlyask.dogfood import DogfoodProject, DogfoodSession, SafeTestRunner
from onlyask.github_adapter import GitHubAdapter


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.head_sha = "abc1234def5678"
        self.merged = False

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if path == "/repos/altrudev/OnlyAsk":
            return {"default_branch": "main", "visibility": "public", "archived": False, "open_issues_count": 2}
        if path == "/repos/altrudev/OnlyAsk/pulls?state=open&per_page=10":
            return [{"number": 7, "title": "Dogfood", "head": {"ref": "dogfood"}, "base": {"ref": "main"}, "html_url": "https://example/pr/7"}]
        if path == "/repos/altrudev/OnlyAsk/pulls/7" and method == "GET":
            return {"number": 7, "title": "Dogfood", "head": {"sha": self.head_sha, "ref": "dogfood"}, "base": {"ref": "main"}, "state": "open" if not self.merged else "closed", "merged": self.merged, "mergeable": True, "html_url": "https://example/pr/7"}
        if path == "/repos/altrudev/OnlyAsk/pulls/7/merge" and method == "PUT":
            assert payload == {"sha": self.head_sha, "merge_method": "squash"}
            self.merged = True
            return {"merged": True, "sha": "mergedsha"}
        raise AssertionError((method, path, payload))


class FakeRunner:
    def run(self, project):
        return {"available": True, "ok": True, "returncode": 0, "command": "python -m pytest -q", "output": "33 passed"}


def session():
    transport = FakeTransport()
    s = DogfoodSession(projects=[DogfoodProject("OnlyAsk", "altrudev/OnlyAsk", "main", "/tmp")], github=GitHubAdapter(transport), runner=FakeRunner())
    return s, transport


def test_inspection_and_tests_are_automatic():
    s, _ = session()
    inspected = s.inspect("altrudev/OnlyAsk")
    tested = s.run_tests("altrudev/OnlyAsk")
    assert inspected.state.value == "verified"
    assert tested.state.value == "verified"
    assert tested.output["ok"] is True
    assert s.pending == {}
    assert s.kernel.ledger.verify_chain()


def test_merge_requires_human_then_uses_exact_one_time_grant():
    s, transport = session()
    requested = s.request_merge("altrudev/OnlyAsk", 7)
    assert requested.state.value == "escalated"
    assert transport.merged is False
    assert requested.transition_id in s.pending
    approved = s.approve_once(requested.transition_id)
    assert approved.state.value == "verified"
    assert transport.merged is True
    assert s.envelope.grants[-1].remaining_uses == 0
    assert s.kernel.ledger.verify_chain()


def test_merge_fails_stale_if_head_changes_after_human_review():
    s, transport = session()
    requested = s.request_merge("altrudev/OnlyAsk", 7)
    transport.head_sha = "changed999999"
    approved = s.approve_once(requested.transition_id)
    assert approved.state.value == "stale"
    assert transport.merged is False


def test_reject_records_human_decision():
    s, _ = session()
    requested = s.request_merge("altrudev/OnlyAsk", 7)
    result = s.reject(requested.transition_id)
    assert result["state"] == "rejected"
    assert not s.pending
    assert s.kernel.ledger.entries[-1].event == "human_rejected"


def test_safe_runner_does_not_accept_arbitrary_command(monkeypatch, tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.1'\n")
    seen = {}
    class Done:
        returncode = 0
        stdout = "ok"
        stderr = ""
    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["cwd"] = kwargs["cwd"]
        seen["shell"] = kwargs.get("shell")
        return Done()
    monkeypatch.setattr("onlyask.dogfood.subprocess.run", fake_run)
    project = DogfoodProject("X", "a/b", local_path=str(tmp_path))
    result = SafeTestRunner().run(project)
    assert result["ok"] is True
    assert seen["command"][1:] == ["-m", "pytest", "-q"]
    assert seen["shell"] is None
