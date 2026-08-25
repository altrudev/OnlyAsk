from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .github_adapter import GitHubAPIError, GitHubAdapter, PullSnapshot
from .kernel import TransitionKernel
from .models import Action, AuthorityEnvelope, Grant, Permission, TransitionResult


@dataclass(frozen=True)
class DogfoodProject:
    name: str
    repo: str
    default_branch: str = "main"
    local_path: str | None = None


class SafeTestRunner:
    """Runs fixed inspection/test commands in an explicitly configured trusted project directory."""

    _ENV_ALLOWLIST = {
        "PATH",
        "HOME",
        "USERPROFILE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "LOCALAPPDATA",
        "APPDATA",
        "VIRTUAL_ENV",
        "PYTHONPATH",
        "PYTHONHOME",
        "LANG",
        "LC_ALL",
    }

    def __init__(self, timeout_seconds: int = 120, output_limit: int = 16000) -> None:
        self.timeout_seconds = timeout_seconds
        self.output_limit = output_limit

    @classmethod
    def sanitized_environment(cls) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if key in cls._ENV_ALLOWLIST}
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def _run_fixed(self, command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
            env=self.sanitized_environment(),
        )

    def run(self, project: DogfoodProject) -> dict[str, Any]:
        if not project.local_path:
            return {"available": False, "ok": False, "message": "No local runner path configured."}
        root = Path(project.local_path).expanduser().resolve()
        if not root.is_dir():
            return {"available": False, "ok": False, "message": "Configured runner path does not exist."}
        marker = root / "pyproject.toml"
        if not marker.exists():
            return {"available": False, "ok": False, "message": "Configured runner path is not a Python project."}

        head = self._run_fixed(["git", "rev-parse", "HEAD"], root)
        tested_sha = head.stdout.strip() if head.returncode == 0 else ""
        if not tested_sha:
            return {
                "available": True,
                "ok": False,
                "returncode": head.returncode,
                "command": "git rev-parse HEAD",
                "output": (head.stdout + head.stderr)[-self.output_limit :],
                "tested_sha": "",
                "message": "Could not bind the test run to an exact Git commit.",
            }

        command = [sys.executable, "-m", "pytest", "-q"]
        completed = self._run_fixed(command, root)
        output = (completed.stdout + completed.stderr)[-self.output_limit :]
        return {
            "available": True,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": "python -m pytest -q",
            "output": output,
            "tested_sha": tested_sha,
        }


@dataclass
class PendingDecision:
    transition_id: str
    kind: str
    title: str
    detail: dict[str, Any]
    action: Action


class DogfoodSession:
    """Real dogfood authority layer for GitHub inspection, safe tests, and PR merge approval."""

    def __init__(
        self,
        projects: list[DogfoodProject] | None = None,
        github: GitHubAdapter | None = None,
        runner: SafeTestRunner | None = None,
    ) -> None:
        local_path = os.getenv("ONLYASK_PROJECT_ROOT") or None
        self.projects = projects or [DogfoodProject("OnlyAsk", "altrudev/OnlyAsk", "main", local_path)]
        self.github = github or GitHubAdapter()
        self.runner = runner or SafeTestRunner()
        self.envelope = AuthorityEnvelope(
            objective=(
                "Operate development projects with minimal interruption: inspect repositories and run "
                "predefined tests automatically; require the owner for merges and other high-impact transitions."
            ),
            allow=[
                Permission("github/*", "read"),
                Permission("runner/*", "test"),
            ],
            deny=[
                Permission("secrets/*", "*"),
                Permission("github/*", "delete"),
                Permission("github/*", "force_push"),
                Permission("github/*", "change_visibility"),
                Permission("github/*", "change_security_policy"),
            ],
            max_mutations=20,
        )
        self.kernel = TransitionKernel(self.envelope)
        self.pending: dict[str, PendingDecision] = {}
        self.last_results: list[dict[str, Any]] = []
        self.last_test_results: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _pull_state_token(pull: PullSnapshot) -> str:
        payload = {
            "repo": pull.repo,
            "number": pull.number,
            "head_sha": pull.head_sha,
            "base_ref": pull.base_ref,
            "state": pull.state,
            "merged": pull.merged,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def project(self, repo: str) -> DogfoodProject:
        for project in self.projects:
            if project.repo == repo:
                return project
        raise KeyError("Project is not configured")

    def inspect(self, repo: str) -> TransitionResult:
        self.project(repo)
        result = self.kernel.run(
            Action(
                resource=f"github/{repo}",
                operation="read",
                purpose=f"Inspect repository {repo}",
                mutating=False,
                execute=lambda: self.github.inspect_repository(repo),
            )
        )
        self._remember("inspect", repo, result)
        return result

    def run_tests(self, repo: str) -> TransitionResult:
        project = self.project(repo)
        result = self.kernel.run(
            Action(
                resource=f"runner/{repo}",
                operation="test",
                purpose=f"Run the predefined test suite for {repo}",
                mutating=False,
                execute=lambda: self.runner.run(project),
            )
        )
        if result.state.value == "verified" and isinstance(result.output, dict):
            self.last_test_results[repo] = dict(result.output)
        self._remember("tests", repo, result)
        return result

    def request_merge(self, repo: str, pr_number: int, method: str = "squash") -> TransitionResult:
        project = self.project(repo)
        pull = self.github.get_pull(repo, pr_number)
        if pull.base_ref != project.default_branch:
            raise ValueError(f"Only merges into {project.default_branch} can be requested from this PWA")
        if pull.state != "open" or pull.merged:
            raise ValueError("Pull request is not open")
        if not pull.head_sha:
            raise ValueError("Pull request head SHA is unavailable")

        tested = self.last_test_results.get(repo)
        if not tested or tested.get("ok") is not True:
            raise ValueError("The predefined test suite must pass before a merge decision can be created")
        if str(tested.get("tested_sha") or "") != pull.head_sha:
            raise ValueError("The last passing test run is not bound to the current pull request head SHA")

        predecessor_token = self._pull_state_token(pull)
        params = {
            "repo": repo,
            "pr_number": pr_number,
            "head_sha": pull.head_sha,
            "tested_sha": str(tested["tested_sha"]),
            "base": pull.base_ref,
            "method": method,
        }

        def current_state_token() -> str:
            return self._pull_state_token(self.github.get_pull(repo, pr_number))

        def execute() -> dict[str, Any]:
            try:
                return self.github.merge_pull(repo, pr_number, pull.head_sha, method)
            except GitHubAPIError:
                # A transport failure can happen after GitHub has already accepted the
                # irreversible merge. Re-read state once and reconcile if the successor
                # is unambiguously observable; otherwise let the kernel mark UNCERTAIN.
                observed = self.github.get_pull(repo, pr_number)
                if observed.merged and observed.merge_commit_sha:
                    return {
                        "merged": True,
                        "sha": observed.merge_commit_sha,
                        "reconciled_after_transport_error": True,
                    }
                raise

        def verify(output: dict[str, Any]) -> bool:
            observed = self.github.get_pull(repo, pr_number)
            merged_sha = str(output.get("sha") or "")
            return (
                bool(output.get("merged"))
                and bool(merged_sha)
                and observed.merged is True
                and observed.base_ref == pull.base_ref
                and observed.merge_commit_sha == merged_sha
            )

        action = Action(
            resource=f"github/{repo}/pull/{pr_number}",
            operation="merge",
            purpose=f"Merge PR #{pr_number} into {pull.base_ref}: {pull.title}",
            parameters=params,
            irreversible=True,
            expected_state_token=predecessor_token,
            read_state_token=current_state_token,
            execute=execute,
            verify=verify,
            recover=None,
        )
        result = self.kernel.run(action)
        if result.state.value == "escalated" and result.transition_id:
            self.pending[result.transition_id] = PendingDecision(
                transition_id=result.transition_id,
                kind="merge",
                title=f"Merge {repo} PR #{pr_number}",
                detail={**params, "title": pull.title, "html_url": pull.html_url},
                action=action,
            )
        self._remember("merge-request", repo, result)
        return result

    def approve_once(self, transition_id: str) -> TransitionResult:
        pending = self.pending.pop(transition_id)
        action = pending.action
        grant = Grant(
            Permission(action.resource, action.operation),
            remaining_uses=1,
            exact_constraints=dict(action.parameters),
        )
        self.envelope.grants.append(grant)
        result = self.kernel.run(action)
        if grant.remaining_uses > 0:
            grant.remaining_uses = 0
            self.kernel.ledger.append(
                result.transition_id or transition_id,
                "scoped_grant_revoked_after_attempt",
                {"approved_transition_id": transition_id, "result_state": result.state.value},
            )
        self._remember("approved", pending.detail.get("repo", ""), result)
        return result

    def reject(self, transition_id: str) -> dict[str, Any]:
        pending = self.pending.pop(transition_id)
        self.kernel.ledger.append(
            transition_id,
            "human_rejected",
            {"kind": pending.kind, "title": pending.title, "detail": pending.detail},
        )
        record = {"transition_id": transition_id, "state": "rejected", "title": pending.title}
        self.last_results.insert(0, record)
        self.last_results = self.last_results[:20]
        return record

    def state(self) -> dict[str, Any]:
        return {
            "objective": self.envelope.objective,
            "projects": [asdict(project) for project in self.projects],
            "pending": [
                {
                    "transition_id": p.transition_id,
                    "kind": p.kind,
                    "title": p.title,
                    "detail": p.detail,
                }
                for p in self.pending.values()
            ],
            "recent": self.last_results[:10],
            "ledger": self.kernel.ledger.export()[-40:],
            "ledger_valid": self.kernel.ledger.verify_chain(),
            "capabilities": {
                "automatic": ["repository inspection", "predefined pytest suite"],
                "ask": ["merge tested pull request into configured default branch"],
                "deny": ["secrets", "repository deletion", "force push", "visibility/security-policy changes"],
            },
        }

    def _remember(self, kind: str, repo: str, result: TransitionResult) -> None:
        output = result.output
        if isinstance(output, dict) and len(str(output)) > 6000:
            output = {**output, "output": str(output.get("output", ""))[-4000:]}
        self.last_results.insert(
            0,
            {
                "kind": kind,
                "repo": repo,
                "transition_id": result.transition_id,
                "state": result.state.value,
                "decision": result.decision.kind.value,
                "message": result.message,
                "output": output,
            },
        )
        self.last_results = self.last_results[:20]
