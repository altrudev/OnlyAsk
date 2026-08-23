from __future__ import annotations

from .models import Action, AuthorityEnvelope, Decision, DecisionKind


class AuthorityEngine:
    """Deterministic authority evaluator. Explicit deny rules override all allows."""

    def evaluate(self, envelope: AuthorityEnvelope, action: Action, mutation_count: int = 0) -> Decision:
        for permission in envelope.deny:
            if permission.matches(action.resource, action.operation):
                return Decision(
                    DecisionKind.DENY,
                    "Action conflicts with an explicit prohibition.",
                    authority_basis=f"deny:{permission.resource}:{permission.action}",
                )

        if action.mutating and envelope.max_mutations is not None and mutation_count >= envelope.max_mutations:
            return Decision(
                DecisionKind.ESCALATE,
                "Mutation budget is exhausted; additional authority is required.",
                authority_basis="constraint:max_mutations",
            )

        if action.mutating and envelope.require_verification and action.verify is None:
            return Decision(
                DecisionKind.DENY,
                "Mutation has no verification method.",
                authority_basis="constraint:require_verification",
            )

        if action.mutating and envelope.require_recovery_for_mutation and action.recover is None:
            return Decision(
                DecisionKind.DENY,
                "Mutation has no recovery path.",
                authority_basis="constraint:require_recovery_for_mutation",
            )

        for index, grant in enumerate(envelope.grants):
            if grant.permits(action):
                return Decision(
                    DecisionKind.ALLOW,
                    "Permitted by a scoped human grant.",
                    authority_basis="scoped_grant",
                    grant_index=index,
                )

        for permission in envelope.allow:
            if permission.matches(action.resource, action.operation):
                return Decision(
                    DecisionKind.ALLOW,
                    "Action falls inside delegated authority.",
                    authority_basis=f"allow:{permission.resource}:{permission.action}",
                )

        return Decision(
            DecisionKind.ESCALATE,
            "No delegated permission covers this action.",
            authority_basis=None,
        )

    @staticmethod
    def consume_grant(envelope: AuthorityEnvelope, decision: Decision) -> None:
        if decision.grant_index is None:
            return
        envelope.grants[decision.grant_index].remaining_uses -= 1
