# OnlyAsk

**Governed Autonomous Operations**

OnlyAsk is built around one rule:

> An agent may act only inside authority already granted to it. It asks the human only when the next meaningful decision actually belongs to the human.

Most agent systems force a bad choice: supervise every step or grant broad permissions. OnlyAsk implements a third model — **bounded autonomy**.

A deterministic transition kernel decides whether a proposed operation is allowed, must be escalated, or is prohibited. Mutations can be bound to observed predecessor state, verified after execution, and recovered when safe recovery exists. External content is evidence, never a new authority source.

## v0.3 — Dogfood PWA

v0.3 turns the governance model into something we can use on real development work: an installable phone control surface backed by a governed GitHub adapter and a constrained test runner.

From the PWA you can:

- inspect the configured repository without human interruption;
- run one predefined pytest suite against a trusted checkout;
- see recent operations and the hash-chained evidence ledger;
- request a PR merge into the configured default branch;
- review that merge in a **Human Decisions** queue;
- approve it once or decline it.

The PWA does **not** receive the GitHub credential. It also does not expose a generic shell, arbitrary GitHub endpoint proxy, repository deletion, force push, visibility changes, or security-policy changes.

### Governed merge semantics

A merge is not authorized merely because the backend technically has a credential capable of performing it.

OnlyAsk first captures the reviewed PR predecessor. Approval is bound to the repository, PR number, head SHA, base branch, open/merged state, and merge method. Before executing, OnlyAsk re-reads the PR. If the head changes or the PR is retargeted after review, the transition becomes **STALE** and no merge occurs.

An approval is one attempted transition. A stale or failed attempt revokes the remaining grant instead of leaving a reusable permission behind. A successful merge is not treated as complete until the returned merge SHA matches the PR's observed merge commit SHA.

See [`docs/DOGFOOD_PWA.md`](docs/DOGFOOD_PWA.md) and the executed [`v0.3 validation record`](docs/VALIDATION_V03.md).

## Run the phone backend locally

```bash
python -m venv .venv
# activate the environment for your OS
pip install -e '.[dev]'
pytest

# configure ONLYASK_PROJECT_ROOT
# configure ONLYASK_GITHUB_TOKEN when GitHub write access is needed
# configure ONLYASK_PWA_TOKEN for non-loopback access
onlyask pwa --host 127.0.0.1 --port 8787
```

Desktop development can use localhost. A real phone installation requires an **HTTPS origin**; a normal `http://<LAN-IP>` address is not sufficient for a service-worker-backed PWA. The next deployment milestone is therefore an authenticated HTTPS edge/tunnel in front of this backend.

## Phone security boundary

- GitHub credentials remain server-side.
- The PWA session credential is separate from the GitHub credential.
- Browser login uses a derived `HttpOnly`, `SameSite=Strict` cookie rather than storing the original token in JavaScript storage.
- Remote cookies are `Secure` by default.
- API state exposes only whether backend credentials are configured, never their values.
- The test subprocess receives a small operating-system environment allowlist, not backend GitHub/AWS/model-provider secrets.
- The test runner has one fixed command and does not use a shell.

The current test runner is intentionally limited to **trusted dogfood repositories**. Python tests remain executable code; a future release should move execution into an OS/container sandbox before untrusted repositories are supported.

## v0.2 — Deterministic product scenario

The earlier governed storefront console remains available and is useful for demonstrating the authority model without credentials:

```bash
onlyask web
```

It demonstrates:

- automatic inspection;
- verified repair;
- a genuine commercial authority escalation;
- a one-use exact-value approval grant;
- hard DNS/credential denial;
- failed-verification recovery;
- hostile directive isolation;
- a hash-chained evidence ledger.

The point is not “AI that asks permission.” The point is **AI that knows when permission already exists, when it does not, and when an action should never be available at all**.

## Evaluate the governance claim

```bash
onlyask eval
onlyask eval --json
```

The deterministic harness covers delegated actions, genuine authority gaps, explicit prohibitions, stale-predecessor blocking, verified mutation, rollback, one-time grant replay prevention, exact-parameter widening, and directive isolation. It reports authority accuracy, expected vs observed human decisions, unsafe allows, unnecessary escalations, and ledger integrity.

The intended invariant is stronger than “all scenarios completed”: **no unsafe allow and no unnecessary human escalation** for the declared evaluation set.

See the executed [`v0.2 validation record`](docs/VALIDATION.md).

## Strands agent

Strands remains the reasoning/tool-selection layer while OnlyAsk keeps authority outside model prompting.

With AWS credentials and Amazon Bedrock model access configured:

```bash
pip install -e .
onlyask agent
```

The reference integration uses `BeforeToolCallEvent` as an independent capability boundary. Mutating tools must additionally invoke `TransitionKernel`; prompting is not the enforcement mechanism.

See [`docs/STRANDS.md`](docs/STRANDS.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Amazon Bedrock AgentCore

OnlyAsk includes an AgentCore Runtime entry point and CodeZip configuration targeting Python 3.13.

```bash
npm install -g @aws/agentcore
agentcore validate
agentcore dev --logs
agentcore deploy
```

AWS is an optional deployment path for the project itself; it is not required for the deterministic console or dogfood authority model. See [`docs/AGENTCORE.md`](docs/AGENTCORE.md).

## Architecture

```text
              human objective + authority
                         |
                         v
                  OnlyAsk gateway
              /          |          \
           ALLOW         ASK        DENY
             |            |           |
             |       phone decision   stop
             |            |
             +------------+
                         |
                         v
                 named adapter action
                   /             \
               GitHub          test runner
                   \             /
                    v           v
                  observe / verify
                         |
                         v
                  evidence ledger
```

For model-driven operation, Strands sits above the same deterministic authority boundary rather than replacing it.

## Core security properties

- explicit resource/action authority;
- deny-overrides-allow evaluation;
- no implicit authority expansion;
- scoped one-time grants with exact constraints;
- predecessor/state-drift checks before sensitive mutation;
- verification as part of the operation;
- recovery where safe recovery exists;
- mutation budgets;
- hash-chained evidence ledger;
- external directive-bearing content treated as evidence, not authority;
- unregistered Strands tools fail closed;
- no unrestricted shell in the reference implementation;
- infrastructure capability is kept separate from task authority.

`EXECUTED` is deliberately not treated as success. Success means the declared postcondition was observed.

## Why this matters beyond the demo

The same authority model can govern site operations, support, cloud administration, commerce operations, internal tooling, browser workflows, and agent-to-agent delegation. Instead of sprinkling confirmation dialogs across every tool, the user defines authority at the task boundary and OnlyAsk preserves it through execution.

That makes the interface quieter for humans and stricter for agents at the same time.

## Project boundary and provenance

OnlyAsk is a standalone project. It does not require H/R Native, DDC, Command0, Calibration Studio, or any private service to function. Prior research into governed autonomous systems informed the problem selection and threat model; the implementation is independently built in this repository. See [`ORIGIN.md`](ORIGIN.md).

Licensed under Apache-2.0.

## Validation status

**v0.3 dogfood delta: PASS** — exact-repository-blob execution of the relevant v0.3 package graph; 11/11 focused tests; Python compilation pass; HTTP/PWA smoke pass including authentication, manifest, service worker, icons, authenticated state, and evidence-chain integrity.

**v0.2 deterministic release: PASS** — historical exact-blob 25/25 tests plus 11/11 governance evaluations, 100% authority accuracy, 0 unsafe allows, 0 unnecessary escalations, and valid evidence ledgers. Those core/test blobs are unchanged by v0.3.

**Complete clone-capable repository pytest for v0.3: PENDING** — this execution environment cannot directly clone the GitHub tree, so the historical v0.2 suite and new v0.3 suite are not being mislabeled as one combined pytest invocation.

**Phone deployment: PENDING** — the code is installable-PWA shaped, but a real phone needs an HTTPS backend plus server-side GitHub and PWA credentials.
