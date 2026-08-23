from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class DecisionKind(str, Enum):
    ALLOW = "allow"
    ESCALATE = "escalate"
    DENY = "deny"


class TransitionState(str, Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    ESCALATED = "escalated"
    DENIED = "denied"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    RECOVERY_FAILED = "recovery_failed"
    STALE = "stale"


@dataclass(frozen=True)
class Permission:
    resource: str
    action: str

    def matches(self, resource: str, action: str) -> bool:
        resource_match = self.resource == resource or self.resource == "*"
        action_match = self.action == action or self.action == "*"
        if self.resource.endswith("/*"):
            resource_match = resource.startswith(self.resource[:-1])
        return resource_match and action_match


@dataclass
class Grant:
    permission: Permission
    remaining_uses: int = 1
    exact_constraints: Mapping[str, Any] = field(default_factory=dict)

    def permits(self, action: Action) -> bool:  # type: ignore[name-defined]
        if self.remaining_uses <= 0 or not self.permission.matches(action.resource, action.operation):
            return False
        return all(action.parameters.get(key) == value for key, value in self.exact_constraints.items())


@dataclass
class AuthorityEnvelope:
    objective: str
    allow: list[Permission] = field(default_factory=list)
    deny: list[Permission] = field(default_factory=list)
    grants: list[Grant] = field(default_factory=list)
    max_mutations: int | None = None
    require_verification: bool = True
    require_recovery_for_mutation: bool = True


Verifier = Callable[[Any], bool]
Executor = Callable[[], Any]
Recovery = Callable[[Any], bool]
StateReader = Callable[[], str]


@dataclass
class Action:
    resource: str
    operation: str
    purpose: str
    parameters: dict[str, Any] = field(default_factory=dict)
    mutating: bool = True
    expected_state_token: str | None = None
    read_state_token: StateReader | None = None
    execute: Executor | None = None
    verify: Verifier | None = None
    recover: Recovery | None = None


@dataclass(frozen=True)
class Decision:
    kind: DecisionKind
    reason: str
    authority_basis: str | None = None
    grant_index: int | None = None


@dataclass
class TransitionResult:
    state: TransitionState
    decision: Decision
    output: Any = None
    verification_passed: bool | None = None
    recovery_passed: bool | None = None
    transition_id: str | None = None
    message: str = ""
