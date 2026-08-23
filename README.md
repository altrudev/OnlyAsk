# OnlyAsk

**Governed Autonomous Operations**

OnlyAsk is an autonomous operations agent architecture built around one rule:

> An agent may act only inside authority already granted to it. It asks the human only when the next meaningful decision actually belongs to the human.

OnlyAsk separates **reasoning** from **authority**. A model may investigate, propose, and explain. A deterministic transition kernel decides whether a proposed operation is allowed, must be escalated, or is prohibited. Mutations are verified against explicit postconditions and recover when verification fails.

## Why this exists

Most autonomous-agent systems force an uncomfortable choice: supervise every step or grant broad permissions. OnlyAsk implements a third model: bounded autonomy.

A task begins with an explicit authority envelope. Every external action is evaluated against that envelope before execution. Low risk never substitutes for permission, and a model cannot silently expand its own authority.

## Core transition

```text
objective
   ↓
authority envelope
   ↓
proposed action
   ↓
ALLOW / ESCALATE / DENY
   ↓
snapshot
   ↓
execute
   ↓
verify
   ↓
VERIFIED / RECOVERED / RECOVERY_FAILED
   ↓
evidence ledger
```

`EXECUTED` is not treated as success. Success means the declared postcondition was observed.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
onlyask demo
```

The deterministic demo requires no model credentials.

For the Strands adapter:

```bash
pip install -e '.[strands]'
```

See `docs/STRANDS.md`.

## Security properties in v0.1

- explicit resource/action authority
- deny-overrides-allow evaluation
- no implicit authority expansion
- scoped one-time grants
- precondition/state-drift checks before mutation
- verification as part of the operation
- rollback on failed verification
- append-only in-memory evidence ledger with hash chaining
- external directive-bearing content treated as evidence, not authority
- no unrestricted shell tool in the reference implementation

## Project boundary

OnlyAsk is a standalone project. It does not require H/R Native, DDC, Calibration Studio, or any private service to function. Prior research into governed autonomous systems informed the problem selection and threat model; this repository is independently implemented and licensed under Apache-2.0. See `ORIGIN.md`.

## Status

v0.1 is the transition kernel and reference demo. The next product layer is a website-repair agent using Strands tools and AWS AgentCore-compatible deployment.
