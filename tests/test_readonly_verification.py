from onlyask.kernel import TransitionKernel
from onlyask.models import Action, AuthorityEnvelope, Permission, TransitionState


def test_read_only_action_can_require_a_verified_postcondition():
    kernel = TransitionKernel(
        AuthorityEnvelope("test", allow=[Permission("runner/*", "test")])
    )
    result = kernel.run(
        Action(
            resource="runner/OnlyAsk",
            operation="test",
            purpose="run tests",
            mutating=False,
            execute=lambda: {"ok": True, "tested_sha": "abc"},
            verify=lambda output: output["ok"] and bool(output["tested_sha"]),
        )
    )

    assert result.state is TransitionState.VERIFIED
    assert result.verification_passed is True
    assert kernel.ledger.verify_chain()


def test_failed_read_only_postcondition_is_not_reported_as_verified():
    kernel = TransitionKernel(
        AuthorityEnvelope("test", allow=[Permission("runner/*", "test")])
    )
    result = kernel.run(
        Action(
            resource="runner/OnlyAsk",
            operation="test",
            purpose="run tests",
            mutating=False,
            execute=lambda: {"ok": False, "tested_sha": "abc"},
            verify=lambda output: output["ok"],
        )
    )

    assert result.state is TransitionState.FAILED
    assert result.verification_passed is False
    assert result.recovery_passed is None
    assert kernel.ledger.entries[-1].event == "verification_failed"
    assert kernel.ledger.verify_chain()
