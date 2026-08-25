import hashlib

from onlyask.kernel import TransitionKernel
from onlyask.ledger import EvidenceLedger
from onlyask.models import Action, AuthorityEnvelope, Grant, Permission, TransitionState


def token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def test_verified_transition_and_ledger_chain():
    state = {"value": "old"}
    snapshot = state["value"]
    kernel = TransitionKernel(AuthorityEnvelope("test", allow=[Permission("website/*", "write")]))
    action = Action(
        resource="website/index",
        operation="write",
        purpose="update",
        expected_state_token=token("old"),
        read_state_token=lambda: token(state["value"]),
        execute=lambda: state.update(value="new") or "new",
        verify=lambda _: state["value"] == "new",
        recover=lambda _: state.update(value=snapshot) is None,
    )
    result = kernel.run(action)
    assert result.state is TransitionState.VERIFIED
    assert kernel.ledger.verify_chain()


def test_failed_verification_recovers():
    state = {"value": "old"}
    kernel = TransitionKernel(AuthorityEnvelope("test", allow=[Permission("website/*", "write")]))
    result = kernel.run(
        Action(
            resource="website/index",
            operation="write",
            purpose="bad update",
            execute=lambda: state.update(value="bad") or "bad",
            verify=lambda _: False,
            recover=lambda _: state.update(value="old") is None,
        )
    )
    assert result.state is TransitionState.RECOVERED
    assert state["value"] == "old"


def test_state_drift_requires_reassessment():
    state = {"value": "changed"}
    executed = {"value": False}
    kernel = TransitionKernel(AuthorityEnvelope("test", allow=[Permission("website/*", "write")]))
    result = kernel.run(
        Action(
            resource="website/index",
            operation="write",
            purpose="stale update",
            expected_state_token=token("original"),
            read_state_token=lambda: token(state["value"]),
            execute=lambda: executed.update(value=True),
            verify=lambda _: True,
            recover=lambda _: True,
        )
    )
    assert result.state is TransitionState.STALE
    assert executed["value"] is False


def test_one_time_grant_is_consumed():
    envelope = AuthorityEnvelope(
        "test",
        grants=[Grant(Permission("dns/www", "write"), remaining_uses=1)],
    )
    kernel = TransitionKernel(envelope)

    def action():
        return Action(
            resource="dns/www",
            operation="write",
            purpose="one time",
            execute=lambda: True,
            verify=lambda _: True,
            recover=lambda _: True,
        )

    assert kernel.run(action()).state is TransitionState.VERIFIED
    assert kernel.run(action()).state is TransitionState.ESCALATED


def test_ledger_detects_tampering():
    ledger = EvidenceLedger()
    entry = ledger.append("tr_test", "proposed", {"a": 1})
    assert ledger.verify_chain()
    object.__setattr__(entry, "entry_hash", "0" * 64)
    assert not ledger.verify_chain()


def irreversible_kernel(execute, verify):
    resource = "github/altrudev/OnlyAsk/pull/7"
    params = {"head_sha": "abc123"}
    envelope = AuthorityEnvelope(
        "test",
        grants=[
            Grant(
                Permission(resource, "merge"),
                exact_constraints=params,
            )
        ],
    )
    kernel = TransitionKernel(envelope)
    action = Action(
        resource=resource,
        operation="merge",
        purpose="merge",
        parameters=params,
        irreversible=True,
        execute=execute,
        verify=verify,
    )
    return kernel, action


def test_irreversible_verified_transition_succeeds_without_recovery_callable():
    kernel, action = irreversible_kernel(lambda: {"sha": "merged"}, lambda _: True)

    result = kernel.run(action)

    assert result.state is TransitionState.VERIFIED
    assert result.verification_passed is True
    assert kernel.envelope.grants[0].remaining_uses == 0
    assert kernel.ledger.verify_chain()


def test_irreversible_execution_exception_is_uncertain():
    def execute():
        raise RuntimeError("connection lost")

    kernel, action = irreversible_kernel(execute, lambda _: True)

    result = kernel.run(action)

    assert result.state is TransitionState.UNCERTAIN
    assert result.recovery_passed is None
    assert any(e.event == "irreversible_outcome_uncertain" for e in kernel.ledger.entries)
    assert kernel.ledger.verify_chain()


def test_irreversible_verification_failure_is_uncertain_without_fake_rollback():
    kernel, action = irreversible_kernel(lambda: {"sha": "maybe"}, lambda _: False)

    result = kernel.run(action)

    assert result.state is TransitionState.UNCERTAIN
    assert result.verification_passed is False
    assert result.recovery_passed is None
    assert not any(e.event == "recovering" for e in kernel.ledger.entries)
    assert kernel.ledger.verify_chain()
