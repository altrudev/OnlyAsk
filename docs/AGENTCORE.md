# Amazon Bedrock AgentCore deployment

OnlyAsk includes a direct-code AgentCore Runtime entry point in `agentcore_main.py` and a CodeZip configuration in `agentcore/agentcore.json`.

## Why Python 3.13

The hackathon submission deadline is after the AgentCore update-block date for the Python 3.10 and 3.11 direct-code runtimes. The committed AgentCore configuration therefore targets `PYTHON_3_13` even though the core OnlyAsk package remains compatible with older Python versions for local development.

## Prerequisites

- AWS account and credentials with the permissions required by AgentCore Runtime;
- Amazon Bedrock model access;
- Node.js 20+;
- Python 3.13 for the deployment environment;
- AWS CDK bootstrapped for the target account/Region when required by the CLI;
- AgentCore CLI installed from `@aws/agentcore`.

The current AWS tooling uses the AgentCore CLI. Do not use the older `bedrock-agentcore-starter-toolkit` flow.

## Local agent check

Install the AgentCore and Strands dependencies:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[agentcore]'
```

The normal OnlyAsk deterministic product console remains available without AWS credentials:

```bash
onlyask web
```

The Strands/Bedrock path can be exercised locally with:

```bash
onlyask agent
```

## AgentCore CLI flow

Install the current CLI:

```bash
npm install -g @aws/agentcore
```

The repository already contains the runtime resource definition. Generate or select the AWS deployment target for your own account/Region using the AgentCore CLI. Local target files are intentionally gitignored.

Run the AgentCore development server from the project root:

```bash
agentcore dev --no-browser --logs
```

Then deploy and invoke:

```bash
agentcore deploy
agentcore invoke "Inspect the storefront and repair anything already inside your authority. Tell me only if a human decision is actually required."
```

## Runtime contract

`agentcore_main.py` uses `BedrockAgentCoreApp` and exposes an `@app.entrypoint` function. Each invocation returns:

- the Strands agent response;
- pending human authority decisions, if any;
- OnlyAsk operation metrics;
- the current evidence-ledger chain validation result.

This keeps the competition demo useful at two levels: judges can see the natural-language agent result and also inspect whether the underlying governed transition path remained valid.

## Security boundary

AgentCore is the deployment/runtime layer, not the authority source. Deployment on AWS does not widen the authority envelope. Strands tool calls are still intercepted by the OnlyAsk capability hook, and mutating tools still have to pass the deterministic transition kernel for predecessor-state checking, execution, verification, recovery, grant consumption, and ledger evidence.

No unrestricted shell or generic arbitrary-write tool is exposed by the reference agent.
