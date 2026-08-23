from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .authority import AuthorityEngine
from .models import Action, AuthorityEnvelope, DecisionKind


@dataclass(frozen=True)
class ToolPolicy:
    resource_from_input: Callable[[dict[str, Any]], str]
    operation: str
    mutating: bool


class StrandsAuthorityHook:
    """BeforeToolCall hook adapter for Strands Agents.

    Importing this module does not require Strands. ``register`` imports the SDK lazily so the
    deterministic kernel remains independently testable.
    """

    def __init__(self, envelope: AuthorityEnvelope, policies: dict[str, ToolPolicy]) -> None:
        self.envelope = envelope
        self.policies = policies
        self.engine = AuthorityEngine()

    def register(self, agent: Any) -> None:
        try:
            from strands.hooks import BeforeToolCallEvent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install OnlyAsk with the 'strands' extra") from exc

        def enforce(event: BeforeToolCallEvent) -> None:
            tool_use = event.tool_use
            name = tool_use["name"] if isinstance(tool_use, dict) else tool_use.name
            params = tool_use.get("input", {}) if isinstance(tool_use, dict) else tool_use.input
            policy = self.policies.get(name)
            if policy is None:
                event.cancel_tool = f"OnlyAsk denied unregistered tool: {name}"
                return

            action = Action(
                resource=policy.resource_from_input(dict(params)),
                operation=policy.operation,
                purpose=f"Strands tool invocation: {name}",
                parameters=dict(params),
                mutating=policy.mutating,
                # The hook is the capability boundary. Mutating tools should additionally call
                # TransitionKernel so verification, recovery, and state-drift checks are enforced.
                verify=(lambda _: True) if policy.mutating else None,
                recover=(lambda _: True) if policy.mutating else None,
            )
            decision = self.engine.evaluate(self.envelope, action)
            if decision.kind is not DecisionKind.ALLOW:
                event.cancel_tool = f"OnlyAsk {decision.kind.value}: {decision.reason}"

        agent.add_hook(enforce, BeforeToolCallEvent)
