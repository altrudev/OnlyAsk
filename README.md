# OnlyAsk

**Governed Autonomous Operations**

OnlyAsk is built around one rule:

> An agent may act only inside authority already granted to it. It asks the human only when the next meaningful decision actually belongs to the human.

Most agent systems force a bad choice: supervise every step or grant broad permissions. OnlyAsk implements a third model — **bounded autonomy**.

A deterministic transition kernel decides whether a proposed operation is allowed, must be escalated, or is prohibited. Transitions can be bound to observed predecessor state, verified after execution, recovered when safe recovery exists, or explicitly classified as irreversible. External content is evidence, never a new authority source.

## v0.3 — Dogfood PWA

v0.3 turns the governance model into something usable on real development work: an installable phone control surface backed by a governed GitHub adapter and constrained test runner.

From the PWA you can:

- inspect the configured repository without human interruption;
- run the predefined pytest suite against a trusted checkout;
- see recent operations and the hash-chained evidence ledger;
- request a PR merge into the configured default branch;
- review that merge in a **Human Decisions** queue;
- approve it once or decline it.

The PWA does **not** receive the GitHub credential. It does not expose a generic shell, arbitrary GitHub endpoint proxy, repository deletion, force push, visibility changes, or security-policy changes.

### Tested-commit merge semantics

A merge is not authorized merely because the backend technically has a credential capable of performing it.

Before a test run can produce merge-eligible evidence, OnlyAsk verifies that the configured checkout has the expected GitHub origin and a clean working tree. It then binds the passing test result to the exact `HEAD` SHA.

A merge decision is bound to the repository, PR number, tested/head SHA, base branch, open/merged state, and merge method. Before execution, OnlyAsk re-reads the PR. If the head or target changes after review, the transition becomes **STALE** and no merge occurs.

A phone approval is one attempted transition. A successful merge is not treated as complete until the returned merge SHA agrees with the observed PR successor. If an irreversible merge outcome becomes ambiguous — for example, a transport failure after GitHub may have accepted it — OnlyAsk reconciles from observed state when possible. Otherwise the transition becomes **UNCERTAIN** and requires manual reconciliation rather than blind retry or fake rollback.

See [`docs/DOGFOOD_PWA.md`](docs/DOGFOOD_PWA.md) and [`docs/VALIDATION_V03.md`](docs/VALIDATION_V03.md).

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

Desktop development can use localhost. A real phone installation requires an **HTTPS origin**; a normal `http://<LAN-IP>` address is not sufficient for a service-worker-backed PWA.

## Phone security boundary

- GitHub credentials remain server-side.
- The PWA session credential is separate from the GitHub credential.
- Browser login uses a derived `HttpOnly`, `SameSite=Strict` cookie rather than storing the original token in JavaScript storage.
- Remote cookies are `Secure` by default.
- API state exposes only whether backend credentials are configured, never their values.
- The test subprocess receives a small operating-system environment allowlist, not backend GitHub/AWS/model-provider secrets.
- The test runner uses fixed commands and never invokes a shell.
- Passing test evidence requires the configured GitHub origin, a clean working tree, an exact Git commit, and a passing pytest result.
- Irreversible ambiguity is visibly surfaced as `UNCERTAIN` on the phone.

The current runner is intentionally limited to **trusted dogfood repositories**. Python tests remain executable code; untrusted repositories require an OS/container sandbox before they should be supported.

## Runtime independence: Strands + Rig

OnlyAsk authority is runtime-neutral. A model framework may select a tool, but it does not become the source of permission.

`src/onlyask/runtime_contract.py` defines the shared runtime capability contract used by the Python/Strands adapter. `conformance/runtime_adapter_cases.json` contains portable ALLOW / ESCALATE / DENY cases for delegated reads/tests, owner-only merge, credential denial, force-push denial, unknown tools, and unprotected mutations.

`adapters/rig/` is a Rust adapter pinned to **Rig 0.42.0**. It uses Rig's pre-tool hook boundary and consumes the same conformance fixture as Python. The Rig adapter is implemented but remains behind a real `cargo test` release gate; source review is not being mislabeled as a Rust compile pass.

## v0.2 deterministic product scenario

The governed storefront console remains useful for demonstrating the authority model without credentials:

```bash
onlyask web
```

It demonstrates automatic inspection, verified repair, a genuine commercial authority escalation, a one-use exact-value approval grant, hard DNS/credential denial, failed-verification recovery, hostile directive isolation, and the evidence ledger.

The point is not “AI that asks permission.” The point is **AI that knows when permission already exists, when it does not, and when an action should never be available at all**.

## Evaluate the governance claim

```bash
onlyask eval
onlyask eval --json
```

The deterministic harness covers delegated actions, genuine authority gaps, explicit prohibitions, stale-predecessor blocking, verified mutation, rollback, one-time grant replay prevention, exact-parameter widening, and directive isolation.

The intended invariant is stronger than “all scenarios completed”: **no unsafe allow and no unnecessary human escalation** for the declared evaluation set.

## Strands agent

Strands remains one reasoning/tool-selection layer while OnlyAsk keeps authority outside model prompting.

With AWS credentials and Amazon Bedrock model access configured:

```bash
pip install -e .
onlyask agent
```

AWS and AgentCore are optional deployment paths for OnlyAsk itself; they are not required for the deterministic console or dogfood PWA architecture.

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
                    runtime adapter
                   /               \
              Strands            Rig
                   \               /
                    named tool surface
                       /         \
                    GitHub     test runner
                       \         /
                    observe / verify
                            |
              recover / stale / uncertain
                            |
                            v
                     evidence ledger
```

## Core security properties

- explicit resource/action authority;
- deny-overrides-allow evaluation;
- no implicit authority expansion;
- scoped one-time grants with exact constraints;
- predecessor/state-drift checks before sensitive mutation;
- read-only and mutating postcondition verification;
- recovery where safe recovery exists;
- explicit irreversible-transition semantics where rollback is not credible;
- mutation budgets;
- hash-chained evidence ledger;
- external directive-bearing content treated as evidence, not authority;
- unknown/unregistered runtime tools fail closed;
- mutating runtime tools require transactional enforcement;
- no unrestricted shell in the reference implementation;
- infrastructure capability is kept separate from task authority.

`EXECUTED` is deliberately not treated as success. Success means the declared postcondition was observed.

## Project boundary and provenance

OnlyAsk is a standalone project. It does not require H/R Native, DDC, Command0, Calibration Studio, or any private service to function. Prior research into governed autonomous systems informed the problem selection and threat model; the implementation is independently built in this repository. See [`ORIGIN.md`](ORIGIN.md).

Licensed under Apache-2.0.

## Validation status

**Python v0.3 branch gate: PASS** — byte-for-byte reconstruction of the current security-sensitive GitHub blobs; **58/58 tests passed** on Python 3.13.5; source/test/entrypoint compilation pass.

**Governance evaluator: PASS** — **11/11 scenarios**, 100% authority accuracy, 0 unsafe allows, 0 unnecessary escalations, and valid evidence ledgers against the modified v0.3 kernel.

**HTTP/PWA smoke gate: PASS** — shell/manifest/service-worker/icons, authentication failure/success, derived cookie authentication, evidence state, secret non-disclosure, and non-loopback auth requirement were exercised. `UNCERTAIN` irreversible outcomes are now visually flagged.

**Rig adapter source/conformance design: IMPLEMENTED; RUST EXECUTION GATE PENDING** — the pinned Rig 0.42.0 crate still requires a Rust-capable host to run `cargo test`. v0.3 should not be merged until that gate is executed.

**Phone HTTPS deployment: PENDING** — installable-PWA code exists, but a real phone needs an authenticated HTTPS backend plus server-side GitHub and PWA credentials.
