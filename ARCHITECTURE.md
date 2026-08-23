# OnlyAsk Architecture

## Design objective

OnlyAsk minimizes unnecessary human interruption without converting autonomy into unlimited authority.

The system therefore separates five responsibilities:

1. **Investigation** — determine relevant state and candidate actions.
2. **Authority evaluation** — determine whether an action is permitted.
3. **Execution** — perform the smallest authorized transition.
4. **Verification** — determine whether the intended postcondition actually holds.
5. **Recovery** — restore prior state when verification fails.

The agent/model participates in (1) and may propose inputs to (2–5), but it is not itself the source of authority.

## Decision semantics

Every proposed external action receives one of three decisions:

- `ALLOW`: already inside delegated authority and operational constraints.
- `ESCALATE`: potentially legitimate, but requires new human authority.
- `DENY`: contradicts an explicit prohibition or a non-negotiable constraint.

Risk does not create authority. A low-risk action can still be denied.

## Transition states

```text
PROPOSED
  ↓
AUTHORIZED ──────────────→ ESCALATED
  ↓                         or DENIED
EXECUTING
  ↓
VERIFYING
  ├────────→ VERIFIED
  └────────→ FAILED
                ↓
             RECOVERING
                ├────→ RECOVERED
                └────→ RECOVERY_FAILED
```

## State-drift rule

Authorization is bound to observed state. Before mutation, the executor rechecks the expected state token/hash. If the resource changed, the transition is not executed under stale authorization; it must be reassessed.

## External directive rule

Content discovered while operating is evidence, not authority. Instructions embedded in web pages, files, retrieved documents, or tool responses cannot overwrite the originating human objective or expand permissions.

## One-time grants

A human escalation may produce a narrow capability rather than widening the entire envelope. Grants can be scoped by resource, action, exact value constraints, use count, and task lifetime.

## Evidence ledger

The ledger stores observable decision evidence and state transitions. It does not store hidden model chain-of-thought. Each entry is hash-linked to the previous entry so accidental or post-hoc modification is detectable within an exported ledger sequence.
