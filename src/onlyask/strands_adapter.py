from __future__ import annotations

from typing import Any

from .ledger import EvidenceLedger
from .models import AuthorityEnvelope, DecisionKind
from .runtime_contract import RuntimeAuthorityGate, RuntimeToolPolicy


ToolPolicy = RuntimeToolPolicy


class StrandsAuthorityHook:
    """BeforeToolCall adapter for Strands using the shared runtime authority gate."""

    def __init__(
        self,
        envelope: AuthorityEnvelope,
        policies: dict[str, ToolPolicy],
        ledger: EvidenceLedger | None = None,
    ) -> None:
        self.gate = RuntimeAuthorityGate("strands", envelope, policies, ledger=ledger)

    def register(self, agent: Any) -> None:
        try:
            from strands.hooks import BeforeToolCallEvent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install the project runtime dependencies first") from exc

        def enforce(event: BeforeToolCallEvent) -> None:
            tool_use = event.tool_use
            name = tool_use["name"] if isinstance(tool_use, dict) else tool_use.name
            params = tool_use.get("input", {}) if isinstance(tool_use, dict) else tool_use.input
            if not isinstance(params, dict):
                params = {}

            result = self.gate.decide(name, dict(params))
            if result.decision.kind is not DecisionKind.ALLOW:
                event.cancel_tool = (
                    f"OnlyAsk {result.decision.kind.value}: {result.decision.reason}"
                )

        agent.add_hook(enforce, BeforeToolCallEvent)
