from __future__ import annotations

import sys
import types

from onlyask.ledger import EvidenceLedger
from onlyask.models import AuthorityEnvelope, Permission
from onlyask.strands_adapter import StrandsAuthorityHook, ToolPolicy


class FakeAgent:
    def __init__(self) -> None:
        self.callback = None

    def add_hook(self, callback, _event_type) -> None:
        self.callback = callback


class FakeEvent:
    def __init__(self, tool_use: dict) -> None:
        self.tool_use = tool_use
        self.cancel_tool = False


def install_fake_strands(monkeypatch) -> None:
    strands = types.ModuleType("strands")
    hooks = types.ModuleType("strands.hooks")

    class BeforeToolCallEvent:
        pass

    hooks.BeforeToolCallEvent = BeforeToolCallEvent
    monkeypatch.setitem(sys.modules, "strands", strands)
    monkeypatch.setitem(sys.modules, "strands.hooks", hooks)


def test_allowed_strands_tool_records_boundary_decision(monkeypatch):
    install_fake_strands(monkeypatch)
    ledger = EvidenceLedger()
    envelope = AuthorityEnvelope(
        objective="Inspect site",
        allow=[Permission("website/*", "read")],
    )
    agent = FakeAgent()
    hook = StrandsAuthorityHook(
        envelope,
        policies={
            "inspect": ToolPolicy(
                resource_from_input=lambda _: "website/index.html",
                operation="read",
                mutating=False,
            )
        },
        ledger=ledger,
    )
    hook.register(agent)

    event = FakeEvent({"name": "inspect", "input": {}, "toolUseId": "abc"})
    agent.callback(event)

    assert event.cancel_tool is False
    assert ledger.entries[-1].event == "strands_tool_authority_decision"
    assert ledger.entries[-1].data["decision"] == "allow"
    assert ledger.entries[-1].data["resource"] == "website/index.html"
    assert ledger.verify_chain()


def test_unregistered_strands_tool_fails_closed_and_is_evidenced(monkeypatch):
    install_fake_strands(monkeypatch)
    ledger = EvidenceLedger()
    agent = FakeAgent()
    hook = StrandsAuthorityHook(AuthorityEnvelope(objective="Inspect site"), {}, ledger=ledger)
    hook.register(agent)

    event = FakeEvent({"name": "shell", "input": {"command": "echo no"}, "toolUseId": "def"})
    agent.callback(event)

    assert "denied unregistered tool" in event.cancel_tool
    assert ledger.entries[-1].data["tool"] == "shell"
    assert ledger.entries[-1].data["decision"] == "deny"
    assert ledger.verify_chain()


def test_mutating_tool_requires_transactional_enforcement_and_is_evidenced(monkeypatch):
    install_fake_strands(monkeypatch)
    ledger = EvidenceLedger()
    envelope = AuthorityEnvelope(
        objective="Repair site",
        allow=[Permission("website/*", "write")],
    )
    agent = FakeAgent()
    hook = StrandsAuthorityHook(
        envelope,
        policies={
            "write_page": ToolPolicy(
                resource_from_input=lambda _: "website/index.html",
                operation="write",
                mutating=True,
                transactional=False,
            )
        },
        ledger=ledger,
    )
    hook.register(agent)

    event = FakeEvent({"name": "write_page", "input": {}, "toolUseId": "ghi"})
    agent.callback(event)

    assert "without transactional enforcement" in event.cancel_tool
    assert ledger.entries[-1].data["decision"] == "deny"
    assert ledger.verify_chain()
