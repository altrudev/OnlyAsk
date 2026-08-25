# OnlyAsk v0.2 validation record

Date: 2026-08-25
Branch: `product-console-v0.2`
Runtime used for deterministic validation: Python 3.13.5

This file records what was actually executed during the v0.2 product pass and keeps unexecuted cloud claims separate from validated behavior.

## Source identity

The execution environment could not resolve GitHub directly. To avoid validating a hand-retyped approximation, the test-relevant files were retrieved through the authenticated GitHub repository interface and reconstructed locally.

Git blob hashes were recomputed locally and compared with the repository blob SHAs before execution.

Result: **16 / 16 test-relevant source and test blobs matched exactly.**

The verified set covered the authority engine, models, ledger, directive classifier, transition kernel, product session, deterministic evaluation harness, Strands authority adapter, package initializer, web console, and all six test modules present at the time of execution.

Subsequent commits in this product pass changed AgentCore configuration, dependency metadata, and documentation; they did not change the deterministic source/test blobs covered by this result.

## Pytest

Command equivalent:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
25 passed in 0.07s
```

## Deterministic governed-autonomy evaluation

The `onlyask.evals.run_evaluations()` harness was executed independently of model credentials.

Result:

| Measure | Result |
| --- | ---: |
| Evaluation cases | 11 / 11 passed |
| Pass rate | 100% |
| Authority accuracy | 100% |
| Unsafe allows | 0 |
| Unnecessary escalations | 0 |
| Expected human decisions | 2 |
| Observed human decisions | 2 |
| Evidence ledgers valid | Yes |

The covered cases include:

- delegated website read;
- delegated website repair;
- commercial authority gap;
- explicit DNS prohibition;
- explicit credential prohibition;
- verified postcondition after an authorized repair;
- failed postcondition with predecessor restoration;
- stale-predecessor execution block;
- one-time grant replay prevention;
- exact-parameter grant widening prevention;
- directive-bearing retrieved content remaining untrusted evidence.

## Python compilation

Command equivalent:

```bash
python -m compileall -q src tests
```

Result: **pass**.

## Product-console smoke test

The deterministic showcase was executed through `OnlyAskConsole`.

Observed result:

```text
showcase results: 6
pending human decisions: 1
asks: 1
completed: 2
denied: 1
recovered: 1
mutations: 2
ledger valid: true
```

This is the intended product story: routine delegated work proceeds, one genuine decision reaches the human, one prohibited transition is denied without escalation, a failed candidate mutation is recovered, and the evidence chain remains valid.

## Static-analysis boundary

`ruff` is declared in the development dependencies, but the validation runtime had no external package-network access and did not have Ruff preinstalled. An attempted installation could not reach the package index.

This is recorded as **tool unavailable**, not as a lint pass or lint failure.

## AgentCore deployment boundary

During the same pass, the AgentCore configuration was checked against the current AgentCore CLI configuration reference and corrected from the obsolete `agents` schema to the current `runtimes` schema. Runtime dependencies were also moved into normal project dependencies because current `agentcore dev` performs a regular `uv sync` in the runtime code location.

The current execution environment does **not** provide:

- authenticated AWS credentials;
- AWS CLI;
- AgentCore CLI;
- installed `bedrock-agentcore` / `strands-agents` packages;
- an AWS/AgentCore connected app through ChatGPT;
- outbound package-network access for installing the missing tooling.

Therefore a real AgentCore deployment and Bedrock model invocation were **not executed in this validation pass**. The repository must not represent them as completed until they have been run in an authenticated AWS environment.

## Release gate

Deterministic product gate: **PASS**.

AgentCore cloud gate: **PENDING AUTHENTICATED AWS EXECUTION**.
