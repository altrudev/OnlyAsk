# Amazon Bedrock AgentCore deployment

OnlyAsk includes a direct-code AgentCore Runtime entry point in `agentcore_main.py` and a current CodeZip project configuration in `agentcore/agentcore.json`.

## Runtime choice

The committed AgentCore configuration targets `PYTHON_3_13`. AgentCore currently supports Python 3.13 for direct code deployment through June 30, 2029, with runtime updates blocked after August 31, 2029. Python 3.10 and 3.11 reach their AgentCore runtime update block on August 31, 2026, so they are not appropriate targets for this September 2026 competition submission.

## Current AgentCore configuration model

The current AgentCore CLI project schema uses a top-level `runtimes` array. Older examples that use a top-level `agents` array are obsolete and are rejected by current CLI releases.

OnlyAsk's configuration uses:

- `runtimes` for the Runtime resource;
- `CodeZip` so weak local hardware does not need a container build;
- `agentcore_main.py` as the direct-code entrypoint;
- project-root `codeLocation` so the package source and deployment entrypoint are packaged together;
- `PYTHON_3_13`;
- public networking and HTTP protocol;
- required empty `memories`, `credentials`, `evaluators`, and `onlineEvalConfigs` arrays.

The JSON schema URI is included in the configuration to make schema drift easier to detect during development.

## Dependencies

Current AgentCore local development runs a normal `uv sync` against the `pyproject.toml` in the runtime's code location. For that reason `bedrock-agentcore` and `strands-agents` are normal runtime dependencies of OnlyAsk rather than optional extras. This ensures the CodeZip runtime contains the packages imported by `agentcore_main.py` and `onlyask.strands_product`.

Development-only tools remain in the `dev` extra.

A `uv.lock` file should be committed after the first dependency resolution in an environment with package-network access. It is intentionally **not gitignored**. The current validation environment could not generate a trustworthy lockfile because it could not reach the package index; the repository does not fabricate one.

## Prerequisites

- AWS account and credentials with the permissions required by AgentCore Runtime;
- Amazon Bedrock model access;
- Node.js 20+;
- Python 3.13 for the deployment environment;
- `uv`;
- AgentCore CLI installed from `@aws/agentcore`;
- AWS infrastructure bootstrap/configuration required by the selected AgentCore target.

## Local deterministic validation

The governance kernel, product scenario, evaluation harness, and browser console do not require AWS credentials:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
onlyask eval
onlyask web
```

## Local Strands / Bedrock validation

With AWS credentials and Bedrock model access configured:

```bash
onlyask agent
```

## AgentCore CLI flow

Install the current CLI:

```bash
npm install -g @aws/agentcore
```

Validate the project configuration before creating infrastructure:

```bash
agentcore validate
```

Run the AgentCore development server from the project root:

```bash
agentcore dev --logs
```

Then deploy and invoke:

```bash
agentcore deploy
agentcore invoke "Inspect the storefront and repair anything already inside your authority. Tell me only if a human decision is actually required."
```

AWS account/Region deployment-target state is deliberately not committed. Local CLI state and secrets are gitignored.

## Runtime contract

`agentcore_main.py` uses `BedrockAgentCoreApp` and exposes an `@app.entrypoint` function. Each invocation returns:

- the Strands agent response;
- pending human authority decisions, if any;
- OnlyAsk operation metrics;
- the current evidence-ledger chain validation result.

This gives the competition demo two inspectable layers: the natural-language agent result and the governed transition evidence underneath it.

## Security boundary

AgentCore is the deployment/runtime layer, not the authority source. Deployment on AWS does not widen the authority envelope. Strands tool calls are intercepted by the OnlyAsk capability hook, and mutating tools must still pass the deterministic transition kernel for predecessor-state checking, execution, verification, recovery, grant consumption, and ledger evidence.

No unrestricted shell or generic arbitrary-write tool is exposed by the reference agent.

## Validation boundary

The deterministic OnlyAsk product has been executed independently of AWS; see `docs/VALIDATION.md`. A real AgentCore cloud deployment still requires an authenticated AWS execution environment with the AgentCore CLI and Bedrock access. The repository does not claim a cloud deployment until that invocation has actually been completed.
