import json
from pathlib import Path

from onlyask.ledger import EvidenceLedger
from onlyask.models import AuthorityEnvelope, DecisionKind, Permission
from onlyask.runtime_contract import RuntimeAuthorityGate, RuntimeToolPolicy


FIXTURE = Path(__file__).parents[1] / "conformance" / "runtime_adapter_cases.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def build_gate(runtime="test-runtime"):
    fixture = load_fixture()
    envelope = AuthorityEnvelope(
        objective=fixture["objective"],
        allow=[Permission(item["resource"], item["action"]) for item in fixture["allow"]],
        deny=[Permission(item["resource"], item["action"]) for item in fixture["deny"]],
    )
    policies = {}
    for case in fixture["cases"]:
        if case.get("registered", True) is False:
            continue
        resource = case.get("resource")
        policies[case["tool"]] = RuntimeToolPolicy(
            resource_from_input=lambda _params, resource=resource: resource,
            operation=case.get("operation", "read"),
            mutating=bool(case.get("mutating", False)),
            transactional=bool(case.get("transactional", False)),
        )
    ledger = EvidenceLedger()
    return RuntimeAuthorityGate(runtime, envelope, policies, ledger), ledger


def test_shared_runtime_conformance_fixture():
    fixture = load_fixture()
    gate, ledger = build_gate()

    for case in fixture["cases"]:
        result = gate.decide(case["tool"], case.get("params", {}))
        assert result.decision.kind.value == case["expected"], case["name"]

    assert ledger.verify_chain()
    assert len(ledger.entries) == len(fixture["cases"])


def test_runtime_specific_evidence_name_is_preserved():
    gate, ledger = build_gate(runtime="strands")
    result = gate.decide("inspect_repository", {"repo": "altrudev/OnlyAsk"})

    assert result.decision.kind is DecisionKind.ALLOW
    assert ledger.entries[-1].event == "strands_tool_authority_decision"
    assert ledger.entries[-1].data["runtime"] == "strands"


def test_invalid_resource_mapping_fails_closed():
    envelope = AuthorityEnvelope(
        objective="test",
        allow=[Permission("github/altrudev/*", "read")],
    )
    gate = RuntimeAuthorityGate(
        "rig",
        envelope,
        {
            "inspect": RuntimeToolPolicy(
                resource_from_input=lambda _: "",
                operation="read",
                mutating=False,
            )
        },
    )

    result = gate.decide("inspect", {})

    assert result.decision.kind is DecisionKind.DENY
    assert result.decision.authority_basis == "runtime:invalid_authority_mapping"


def test_unregistered_tool_never_inherits_wildcard_allow():
    envelope = AuthorityEnvelope(objective="test", allow=[Permission("*", "*")])
    gate = RuntimeAuthorityGate("rig", envelope, {})

    result = gate.decide("shell", {"command": "echo no"})

    assert result.decision.kind is DecisionKind.DENY
    assert result.decision.authority_basis == "runtime:unregistered_tool"
