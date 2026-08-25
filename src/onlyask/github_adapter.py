from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request


class GitHubAPIError(RuntimeError):
    pass


class GitHubTransport(Protocol):
    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any: ...


class UrllibGitHubTransport:
    """Small GitHub REST transport. The token never leaves the backend process."""

    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("ONLYASK_GITHUB_TOKEN", "")
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/repos/"):
            raise ValueError("Only repository-scoped GitHub endpoints are permitted")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "OnlyAsk-Dogfood-PWA/0.3",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(self.base_url + path, data=body, headers=headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=20) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise GitHubAPIError(f"GitHub API {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise GitHubAPIError(f"GitHub API unavailable: {exc.reason}") from exc
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


@dataclass(frozen=True)
class PullSnapshot:
    repo: str
    number: int
    title: str
    head_sha: str
    head_ref: str
    base_ref: str
    state: str
    merged: bool
    mergeable: bool | None
    html_url: str


class GitHubAdapter:
    def __init__(self, transport: GitHubTransport | None = None) -> None:
        self.transport = transport or UrllibGitHubTransport()

    @staticmethod
    def _repo(repo: str) -> str:
        parts = repo.strip().split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Repository must be owner/name")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if any(any(ch not in allowed for ch in part) for part in parts):
            raise ValueError("Repository contains unsupported characters")
        return "/".join(parts)

    def inspect_repository(self, repo: str) -> dict[str, Any]:
        repo = self._repo(repo)
        metadata = self.transport.request("GET", f"/repos/{repo}")
        pulls = self.transport.request("GET", f"/repos/{repo}/pulls?state=open&per_page=10")
        return {
            "repo": repo,
            "default_branch": metadata.get("default_branch"),
            "visibility": metadata.get("visibility", "public" if not metadata.get("private") else "private"),
            "archived": bool(metadata.get("archived", False)),
            "open_issues": int(metadata.get("open_issues_count", 0)),
            "open_pulls": [
                {
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "head": (p.get("head") or {}).get("ref"),
                    "base": (p.get("base") or {}).get("ref"),
                    "html_url": p.get("html_url"),
                }
                for p in pulls
            ],
        }

    def get_pull(self, repo: str, number: int) -> PullSnapshot:
        repo = self._repo(repo)
        if number < 1:
            raise ValueError("Pull request number must be positive")
        p = self.transport.request("GET", f"/repos/{repo}/pulls/{number}")
        return PullSnapshot(
            repo=repo,
            number=number,
            title=str(p.get("title", "")),
            head_sha=str((p.get("head") or {}).get("sha", "")),
            head_ref=str((p.get("head") or {}).get("ref", "")),
            base_ref=str((p.get("base") or {}).get("ref", "")),
            state=str(p.get("state", "")),
            merged=bool(p.get("merged", False)),
            mergeable=p.get("mergeable"),
            html_url=str(p.get("html_url", "")),
        )

    def merge_pull(self, repo: str, number: int, expected_head_sha: str, method: str = "squash") -> dict[str, Any]:
        repo = self._repo(repo)
        if method not in {"merge", "squash", "rebase"}:
            raise ValueError("Unsupported merge method")
        if not expected_head_sha or len(expected_head_sha) < 7:
            raise ValueError("Expected head SHA is required")
        return self.transport.request(
            "PUT",
            f"/repos/{repo}/pulls/{number}/merge",
            {"sha": expected_head_sha, "merge_method": method},
        )
