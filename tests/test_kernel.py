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
