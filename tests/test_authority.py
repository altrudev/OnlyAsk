from onlyask.authority import AuthorityEngine
from onlyask.models import Action, AuthorityEnvelope, DecisionKind, Grant, Permission


def mutation(resource="website/index.html", operation="write", **parameters):
    return Action(
        resource=resource,
        operation=operation,
        purpose="test",
        parameters=parameters,
        verify=lambda _: True,
        recover=lambda _: True,
    )


def test_explicit_deny_overrides_allow():
    envelope = AuthorityEnvelope(
        objective="test",
        allow=[Permission("*", "*")],
        deny=[Permission("dns/*", "*")],
    )
    decision = AuthorityEngine().evaluate(envelope, mutation("dns/www", "write"))
    assert decision.kind is DecisionKind.DENY


def test_unknown_authority_escalates():
    envelope = AuthorityEnvelope(objective="test", allow=[Permission("website/*", "write")])
    decision = AuthorityEngine().evaluate(envelope, mutation("dns/www", "write"))
    assert decision.kind is DecisionKind.ESCALATE


def test_scoped_grant_matches_exact_constraint():
    envelope = AuthorityEnvelope(
        objective="test",
        grants=[Grant(Permission("dns/www", "write"), exact_constraints={"value": "192.0.2.18"})],
    )
    allowed = AuthorityEngine().evaluate(envelope, mutation("dns/www", "write", value="192.0.2.18"))
    wrong = AuthorityEngine().evaluate(envelope, mutation("dns/www", "write", value="203.0.113.8"))
    assert allowed.kind is DecisionKind.ALLOW
    assert wrong.kind is DecisionKind.ESCALATE


def test_mutation_without_verification_fails_closed():
    envelope = AuthorityEnvelope(objective="test", allow=[Permission("website/*", "write")])
    action = Action(
        resource="website/a",
        operation="write",
        purpose="test",
        recover=lambda _: True,
    )
    assert AuthorityEngine().evaluate(envelope, action).kind is DecisionKind.DENY


def test_irreversible_mutation_never_inherits_broad_delegated_allow():
    envelope = AuthorityEnvelope(objective="test", allow=[Permission("github/*", "merge")])
    action = Action(
        resource="github/altrudev/OnlyAsk/pull/7",
        operation="merge",
        purpose="merge",
        parameters={"head_sha": "abc123"},
        irreversible=True,
        verify=lambda _: True,
    )

    decision = AuthorityEngine().evaluate(envelope, action)

    assert decision.kind is DecisionKind.ESCALATE
    assert decision.authority_basis == "constraint:irreversible_requires_scoped_grant"


def test_irreversible_mutation_accepts_exact_scoped_grant_without_fake_recovery():
    action = Action(
        resource="github/altrudev/OnlyAsk/pull/7",
        operation="merge",
        purpose="merge",
        parameters={"head_sha": "abc123"},
        irreversible=True,
        verify=lambda _: True,
    )
    envelope = AuthorityEnvelope(
        objective="test",
        grants=[
            Grant(
                Permission(action.resource, action.operation),
                exact_constraints={"head_sha": "abc123"},
            )
        ],
    )

    decision = AuthorityEngine().evaluate(envelope, action)

    assert decision.kind is DecisionKind.ALLOW
    assert decision.authority_basis == "scoped_grant"


def test_irreversible_exact_grant_does_not_allow_parameter_widening():
    envelope = AuthorityEnvelope(
        objective="test",
        grants=[
            Grant(
                Permission("github/altrudev/OnlyAsk/pull/7", "merge"),
                exact_constraints={"head_sha": "approved"},
            )
        ],
    )
    action = Action(
        resource="github/altrudev/OnlyAsk/pull/7",
        operation="merge",
        purpose="merge",
        parameters={"head_sha": "different"},
        irreversible=True,
        verify=lambda _: True,
    )

    decision = AuthorityEngine().evaluate(envelope, action)

    assert decision.kind is DecisionKind.ESCALATE
