from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .authority import AuthorityEngine
from .ledger import EvidenceLedger
from .models import Action, AuthorityEnvelope, DecisionKind


@dataclass(frozen=True)
class ToolPolicy:
    resource_from_input: Callable[[dict[str, Any]], str]
    operation: str
    mutating: bool
    transactional: bool = False


class StrandsAuthorityHook:
    """BeforeToolCall hook adapter for Strands Agents.

    Importing this module does not require Strands. ``register`` imports the SDK lazily so the
    deterministic kernel remains independently testable.
    """

    def __init__(
        self,
        envelope: AuthorityEnvelope,
        policies: dict[str, ToolPolicy],
        ledger: EvidenceLedger | None = None,
    ) -> None:
        self.envelope = envelope
        self.policies = policies
        self.engine = AuthorityEngine()
        self.ledger = ledger

    def register(self, agent: Any) -> None:
        try:
            from strands.hooks import BeforeToolCallEvent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install OnlyAsk with the 'strands' extra") from exc

        def enforce(event: BeforeToolCallEvent) -> None:
            tool_use = event.tool_use
            name = tool_use["name"] if isinstance(tool_use, dict) else tool_use.name
            params = tool_use.get("input", {}) if isinstance(tool_use, dict) else tool_use.input
            tool_use_id = (
                tool_use.get("toolUseId")
                if isinstance(tool_use, dict)
                else getattr(tool_use, "toolUseId", None)
            )
            evidence_id = f"strands_{tool_use_id or uuid.uuid4().hex[:12]}"
            policy = self.policies.get(name)

            if policy is None:
                self._record(
                    evidence_id,
                    name,
                    "deny",
                    "Tool is not registered in the capability surface.",
                    None,
                )
                event.cancel_tool = f"OnlyAsk denied unregistered tool: {name}"
                return

            if policy.mutating and not policy.transactional:
                reason = f"Mutating tool lacks transactional enforcement: {name}"
                self._record(evidence_id, name, "deny", reason, None)
                event.cancel_tool = (
                    f"OnlyAsk denied mutating tool without transactional enforcement: {name}"
                )
                return

            action = Action(
                resource=policy.resource_from_input(dict(params)),
                operation=policy.operation,
                purpose=f"Strands tool invocation: {name}",
                parameters=dict(params),
                mutating=policy.mutating,
                # The hook is the capability boundary. Transactional mutating tools additionally
                # call TransitionKernel for verification, recovery, and state-drift enforcement.
                verify=(lambda _: True) if policy.mutating else None,
                recover=(lambda _: True) if policy.mutating else None,
            )
            decision = self.engine.evaluate(self.envelope, action)
            self._record(
                evidence_id,
                name,
                decision.kind.value,
                decision.reason,
                decision.authority_basis,
                resource=action.resource,
                operation=action.operation,
            )
            if decision.kind is not DecisionKind.ALLOW:
                event.cancel_tool = f"OnlyAsk {decision.kind.value}: {decision.reason}"

        agent.add_hook(enforce, BeforeToolCallEvent)

    def _record(
        self,
        evidence_id: str,
        tool_name: str,
        decision: str,
        reason: str,
        authority_basis: str | None,
        *,
        resource: str | None = None,
        operation: str | None = None,
    ) -> None:
        if self.ledger is None:
            return
        self.ledger.append(
            evidence_id,
            "strands_tool_authority_decision",
            {
                "tool": tool_name,
                "decision": decision,
                "reason": reason,
                "authority_basis": authority_basis,
                "resource": resource,
                "operation": operation,
            },
        )
