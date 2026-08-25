from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .github_adapter import GitHubAdapter
from .kernel import TransitionKernel
from .models import Action, AuthorityEnvelope, Grant, Permission, TransitionResult


@dataclass(frozen=True)
class DogfoodProject:
    name: str
    repo: str
    default_branch: str = "main"
    local_path: str | None = None


class SafeTestRunner:
    """Runs one fixed test command in an explicitly configured project directory."""

    def __init__(self, timeout_seconds: int = 120, output_limit: int = 16000) -> None:
        self.timeout_seconds = timeout_seconds
        self.output_limit = output_limit

    def run(self, project: DogfoodProject) -> dict[str, Any]:
        if not project.local_path:
            return {"available": False, "ok": False, "message": "No local runner path configured."}
        root = Path(project.local_path).expanduser().resolve()
        if not root.is_dir():
            return {"available": False, "ok": False, "message": "Configured runner path does not exist."}
        marker = root / "pyproject.toml"
        if not marker.exists():
            return {"available": False, "ok": False, "message": "Configured runner path is not a Python project."}
        command = [sys.executable, "-m", "pytest", "-q"]
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        output = (completed.stdout + completed.stderr)[-self.output_limit :]
        return {
            "available": True,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": "python -m pytest -q",
            "output": output,
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

        params = {
            "repo": repo,
            "pr_number": pr_number,
            "head_sha": pull.head_sha,
            "base": pull.base_ref,
            "method": method,
        }

        def current_head() -> str:
            return self.github.get_pull(repo, pr_number).head_sha

        def execute() -> dict[str, Any]:
            return self.github.merge_pull(repo, pr_number, pull.head_sha, method)

        def verify(_: dict[str, Any]) -> bool:
            observed = self.github.get_pull(repo, pr_number)
            return observed.merged is True and observed.base_ref == pull.base_ref

        action = Action(
            resource=f"github/{repo}/pull/{pr_number}",
            operation="merge",
            purpose=f"Merge PR #{pr_number} into {pull.base_ref}: {pull.title}",
            parameters=params,
            expected_state_token=pull.head_sha,
            read_state_token=current_head,
            execute=execute,
            verify=verify,
            recover=lambda _: False,
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
        self.envelope.grants.append(
            Grant(
                Permission(action.resource, action.operation),
                remaining_uses=1,
                exact_constraints=dict(action.parameters),
            )
        )
        result = self.kernel.run(action)
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
                "ask": ["merge pull request into configured default branch"],
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
