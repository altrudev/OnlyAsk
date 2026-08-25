from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .authority import AuthorityEngine
from .ledger import EvidenceLedger
from .models import Action, AuthorityEnvelope, Decision, DecisionKind


@dataclass(frozen=True)
class RuntimeToolPolicy:
    """Runtime-neutral mapping from a model-visible tool to OnlyAsk authority."""

    resource_from_input: Callable[[dict[str, Any]], str]
    operation: str
    mutating: bool
    transactional: bool = False


@dataclass(frozen=True)
class RuntimeDecision:
    runtime: str
    tool_name: str
    resource: str | None
    operation: str | None
    decision: Decision


class RuntimeAuthorityGate:
    """Common authority boundary shared by Strands, Rig, and future runtimes.

    This gate does not execute tools. It answers the capability question that must
    be resolved before a runtime is permitted to dispatch a tool. Transactional
    mutation still belongs to TransitionKernel inside the actual tool body.
    """

    def __init__(
        self,
        runtime: str,
        envelope: AuthorityEnvelope,
        policies: dict[str, RuntimeToolPolicy],
        ledger: EvidenceLedger | None = None,
    ) -> None:
        if not runtime.strip():
            raise ValueError("runtime name is required")
        self.runtime = runtime.strip()
        self.envelope = envelope
        self.policies = policies
        self.ledger = ledger
        self.engine = AuthorityEngine()

    def decide(self, tool_name: str, params: dict[str, Any]) -> RuntimeDecision:
        policy = self.policies.get(tool_name)
        evidence_id = f"{self.runtime}_tool_{tool_name}"

        if policy is None:
            decision = Decision(
                DecisionKind.DENY,
                "Tool is not registered in the capability surface.",
                authority_basis="runtime:unregistered_tool",
            )
            self._record(evidence_id, tool_name, None, None, decision)
            return RuntimeDecision(self.runtime, tool_name, None, None, decision)

        if policy.mutating and not policy.transactional:
            decision = Decision(
                DecisionKind.DENY,
                "Mutating tool lacks transactional enforcement.",
                authority_basis="runtime:transaction_required",
            )
            resource = self._resource(policy, params)
            self._record(evidence_id, tool_name, resource, policy.operation, decision)
            return RuntimeDecision(
                self.runtime, tool_name, resource, policy.operation, decision
            )

        try:
            resource = self._resource(policy, params)
        except Exception as exc:
            decision = Decision(
                DecisionKind.DENY,
                f"Tool input could not be mapped to authority: {type(exc).__name__}.",
                authority_basis="runtime:invalid_authority_mapping",
            )
            self._record(evidence_id, tool_name, None, policy.operation, decision)
            return RuntimeDecision(self.runtime, tool_name, None, policy.operation, decision)

        action = Action(
            resource=resource,
            operation=policy.operation,
            purpose=f"{self.runtime} tool invocation: {tool_name}",
            parameters=dict(params),
            mutating=policy.mutating,
            # The runtime gate is only the capability boundary. A transactional
            # mutating tool must still call TransitionKernel for real execution,
            # verification, recovery and scoped-grant consumption.
            verify=(lambda _: True) if policy.mutating else None,
            recover=(lambda _: True) if policy.mutating else None,
        )
        decision = self.engine.evaluate(self.envelope, action)
        self._record(evidence_id, tool_name, resource, policy.operation, decision)
        return RuntimeDecision(
            self.runtime, tool_name, resource, policy.operation, decision
        )

    @staticmethod
    def _resource(policy: RuntimeToolPolicy, params: dict[str, Any]) -> str:
        resource = policy.resource_from_input(dict(params))
        if not isinstance(resource, str) or not resource.strip():
            raise ValueError("empty authority resource")
        return resource.strip()

    def _record(
        self,
        evidence_id: str,
        tool_name: str,
        resource: str | None,
        operation: str | None,
        decision: Decision,
    ) -> None:
        if self.ledger is None:
            return
        self.ledger.append(
            evidence_id,
            "runtime_tool_authority_decision",
            {
                "runtime": self.runtime,
                "tool": tool_name,
                "decision": decision.kind.value,
                "reason": decision.reason,
                "authority_basis": decision.authority_basis,
                "resource": resource,
                "operation": operation,
            },
        )
