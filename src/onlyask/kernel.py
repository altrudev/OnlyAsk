from __future__ import annotations

import uuid

from .authority import AuthorityEngine
from .ledger import EvidenceLedger
from .models import Action, AuthorityEnvelope, DecisionKind, TransitionResult, TransitionState


class TransitionKernel:
    """Executes governed transitions while preserving authority and recovery semantics."""

    def __init__(self, envelope: AuthorityEnvelope, ledger: EvidenceLedger | None = None) -> None:
        self.envelope = envelope
        self.ledger = ledger or EvidenceLedger()
        self.authority = AuthorityEngine()
        self.mutation_count = 0

    def run(self, action: Action) -> TransitionResult:
        transition_id = f"tr_{uuid.uuid4().hex[:12]}"
        self.ledger.append(
            transition_id,
            "proposed",
            {
                "resource": action.resource,
                "operation": action.operation,
                "purpose": action.purpose,
                "mutating": action.mutating,
                "irreversible": action.irreversible,
            },
        )

        decision = self.authority.evaluate(self.envelope, action, self.mutation_count)
        self.ledger.append(
            transition_id,
            "authority_decision",
            {
                "decision": decision.kind.value,
                "reason": decision.reason,
                "basis": decision.authority_basis,
            },
        )

        if decision.kind is DecisionKind.DENY:
            return TransitionResult(
                TransitionState.DENIED,
                decision,
                transition_id=transition_id,
                message=decision.reason,
            )
        if decision.kind is DecisionKind.ESCALATE:
            return TransitionResult(
                TransitionState.ESCALATED,
                decision,
                transition_id=transition_id,
                message=decision.reason,
            )

        if action.expected_state_token is not None:
            if action.read_state_token is None:
                return self._fail_closed(transition_id, decision, "Expected state supplied without state reader.")
            current_token = action.read_state_token()
            if current_token != action.expected_state_token:
                self.ledger.append(
                    transition_id,
                    "state_drift",
                    {"expected": action.expected_state_token, "observed": current_token},
                )
                return TransitionResult(
                    TransitionState.STALE,
                    decision,
                    transition_id=transition_id,
                    message="Resource state changed after assessment; reassessment required.",
                )

        if action.execute is None:
            return self._fail_closed(transition_id, decision, "Authorized action has no executor.")

        self.ledger.append(transition_id, "executing", {})
        try:
            output = action.execute()
        except Exception as exc:
            self.ledger.append(transition_id, "execution_failed", {"error": type(exc).__name__})
            if action.irreversible:
                self.ledger.append(
                    transition_id,
                    "irreversible_outcome_uncertain",
                    {"phase": "execution", "error": type(exc).__name__},
                )
                return TransitionResult(
                    TransitionState.UNCERTAIN,
                    decision,
                    transition_id=transition_id,
                    message=(
                        "Irreversible execution did not return a reliable outcome; "
                        "manual reconciliation is required."
                    ),
                )
            return TransitionResult(
                TransitionState.FAILED,
                decision,
                transition_id=transition_id,
                message="Execution failed before verification.",
            )

        if action.mutating:
            self.mutation_count += 1
            self.authority.consume_grant(self.envelope, decision)

        if not action.mutating:
            self.ledger.append(transition_id, "verified", {"mode": "non_mutating"})
            return TransitionResult(
                TransitionState.VERIFIED,
                decision,
                output=output,
                verification_passed=True,
                transition_id=transition_id,
                message="Non-mutating action completed.",
            )

        assert action.verify is not None
        self.ledger.append(transition_id, "verifying", {})
        try:
            verification_passed = bool(action.verify(output))
        except Exception:
            verification_passed = False

        if verification_passed:
            self.ledger.append(transition_id, "verified", {})
            return TransitionResult(
                TransitionState.VERIFIED,
                decision,
                output=output,
                verification_passed=True,
                transition_id=transition_id,
                message="Postcondition verified.",
            )

        self.ledger.append(transition_id, "verification_failed", {})
        if action.irreversible:
            self.ledger.append(
                transition_id,
                "irreversible_outcome_uncertain",
                {"phase": "verification"},
            )
            return TransitionResult(
                TransitionState.UNCERTAIN,
                decision,
                output=output,
                verification_passed=False,
                transition_id=transition_id,
                message=(
                    "Irreversible action returned but its postcondition could not be verified; "
                    "manual reconciliation is required."
                ),
            )

        assert action.recover is not None
        self.ledger.append(transition_id, "recovering", {})
        try:
            recovered = bool(action.recover(output))
        except Exception:
            recovered = False

        state = TransitionState.RECOVERED if recovered else TransitionState.RECOVERY_FAILED
        self.ledger.append(transition_id, state.value, {})
        return TransitionResult(
            state,
            decision,
            output=output,
            verification_passed=False,
            recovery_passed=recovered,
            transition_id=transition_id,
            message="Verification failed; recovery succeeded." if recovered else "Verification and recovery failed.",
        )

    def _fail_closed(self, transition_id, decision, message: str) -> TransitionResult:
        self.ledger.append(transition_id, "failed_closed", {"message": message})
        return TransitionResult(
            TransitionState.DENIED,
            decision,
            transition_id=transition_id,
            message=message,
        )
