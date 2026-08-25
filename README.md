# OnlyAsk

**Governed Autonomous Operations**

OnlyAsk is an autonomous operations agent built around one rule:

> An agent may act only inside authority already granted to it. It asks the human only when the next meaningful decision actually belongs to the human.

Most agent systems force a bad choice: supervise every step or grant broad permissions. OnlyAsk implements a third model — **bounded autonomy**.

Strands Agents handles reasoning and tool selection. A deterministic transition kernel independently decides whether a proposed operation is allowed, must be escalated, or is prohibited. Mutations are bound to observed predecessor state, verified after execution, and recovered when verification fails.

## The product

The v0.2 judge demo is a governed website-operations console. Give the agent a goal such as keeping a storefront healthy and define the authority boundary once.

OnlyAsk can then:

- inspect the site without interrupting the human;
- repair an already-authorized broken link and verify the result;
- surface a price change as a narrow human decision instead of requesting blanket access;
- convert approval into a one-use, exact-value grant;
- hard-deny prohibited DNS or credential actions without bothering the human;
- roll back a mutation that fails its postcondition;
- isolate prompt-injection-style page instructions as untrusted evidence;
- expose the observable decision path through a hash-chained evidence ledger.

The point is not “AI that asks permission.” The point is **AI that knows when permission already exists, when it does not, and when an action should never be available at all**.

## Run the interactive console

No model credentials are required for the deterministic judge scenario.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
onlyask web
```

Open `http://127.0.0.1:8765`.

Use **Run end-to-end showcase** to exercise the complete story: automatic inspection → verified repair → human escalation → explicit denial → failed verification/recovery → hostile directive isolation.

## Evaluate the product claim

OnlyAsk includes a deterministic evaluation harness so the governance claim can be tested independently of model variability or credentials.

```bash
onlyask eval
onlyask eval --json
```

The harness covers delegated actions, genuine authority gaps, explicit prohibitions, stale-predecessor blocking, verified mutation, rollback, one-time grant replay prevention, exact-parameter widening, and directive isolation. Its summary reports authority accuracy, expected vs observed human decisions, unsafe allows, unnecessary escalations, and ledger integrity.

The intended invariant is stronger than “all scenarios completed”: **no unsafe allow and no unnecessary human escalation** for the declared evaluation set.

See the executed [`v0.2 validation record`](docs/VALIDATION.md).

## Run the Strands agent

Strands and the AgentCore SDK are runtime dependencies because the AgentCore CodeZip development flow performs a normal project dependency sync.

With AWS credentials and Amazon Bedrock model access configured:

```bash
pip install -e .
onlyask agent
```

The reference Strands integration uses `BeforeToolCallEvent` as an independent capability boundary. Mutating tools must additionally invoke `TransitionKernel`; prompt instructions are never treated as the enforcement mechanism.

See [`docs/STRANDS.md`](docs/STRANDS.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Amazon Bedrock AgentCore

OnlyAsk includes an AgentCore Runtime entry point and a current CodeZip configuration using the CLI's `runtimes` schema. The committed runtime target is **Python 3.13**.

```bash
npm install -g @aws/agentcore
agentcore validate
agentcore dev --logs
agentcore deploy
```

AWS account/Region target state is deliberately not committed. See [`docs/AGENTCORE.md`](docs/AGENTCORE.md) for the deployment flow and [`docs/VALIDATION.md`](docs/VALIDATION.md) for the boundary between executed validation and the pending authenticated AWS deployment.

## Architecture

```text
human objective + authority envelope
               ↓
        Strands reasoning
               ↓
    before-tool authority gate
        ↙      ↓       ↘
     DENY   ESCALATE   ALLOW
              ↓          ↓
       scoped human    transition
          decision       kernel
              ↓          ↓
         one-time     execute
           grant         ↓
                    verify
                    ↙    ↘
                recover  verified
                    ↘    ↙
                 evidence ledger
```

A full Mermaid architecture diagram is in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Core security properties

- explicit resource/action authority;
- deny-overrides-allow evaluation;
- no implicit authority expansion;
- scoped one-time grants with exact constraints;
- precondition/state-drift checks before mutation;
- verification as part of the operation;
- rollback on failed verification;
- mutation budgets;
- hash-chained evidence ledger;
- external directive-bearing content treated as evidence, not authority;
- unregistered Strands tools fail closed;
- mutating Strands tools require transactional enforcement;
- no unrestricted shell tool in the reference implementation.

`EXECUTED` is deliberately not treated as success. Success means the declared postcondition was observed.

## Why this is useful beyond the demo

The same authority model can govern repetitive work in site operations, support, cloud administration, commerce operations, internal tooling, and agent-driven browser workflows. Instead of sprinkling confirmation dialogs across every tool, the user defines authority at the task boundary and OnlyAsk preserves it through execution.

That makes the interface quieter for humans and stricter for agents at the same time.

## Project boundary and competition provenance

OnlyAsk is a standalone project created during the 2026 Agents for Humans submission period. It does not require H/R Native, DDC, Calibration Studio, or any private service to function. Prior research into governed autonomous systems informed the problem selection and threat model; the submitted implementation is independently built in this repository. See [`ORIGIN.md`](ORIGIN.md).

Licensed under Apache-2.0.

## Status

**Deterministic v0.2 gate: PASS** — 25/25 tests, 11/11 governance evaluations, 100% authority accuracy, 0 unsafe allows, 0 unnecessary escalations, valid evidence ledgers, compilation pass, and product-console smoke pass.

**AgentCore configuration gate: PASS against the current published CLI model** — current `runtimes` schema, CodeZip, Python 3.13, and runtime dependencies are represented in the repository.

**AgentCore cloud gate: PENDING AUTHENTICATED AWS EXECUTION** — a real deployment still requires an authenticated AWS execution environment with the AgentCore CLI and Bedrock access.

Next competition milestones are that AgentCore deployment, a public live demo, model-driven evaluation traces, and the final ≤5-minute submission video.
