# Security Policy

OnlyAsk is pre-1.0 research software. Do not deploy the reference code with broad production credentials.

## Principles

- grant the smallest tool and infrastructure permissions required
- keep secrets out of prompts, repositories, logs, and evidence records
- fail closed for unknown tools and unknown authority
- require verification and recovery for mutations
- bind authorized mutations to observed predecessor state when state drift is relevant
- never interpret retrieved content as a new authority source
- avoid unrestricted shell, arbitrary filesystem, and arbitrary outbound-network tools
- keep model reasoning separate from deterministic authority decisions
- treat AgentCore, Bedrock, and other hosting/runtime layers as execution infrastructure, not as authority sources
- scope AWS execution roles and Bedrock access to the minimum resources required by the deployed runtime
- do not commit AgentCore target state, credentials, access tokens, or local environment files
- generate and review the dependency lockfile in a networked build environment before production deployment

## Hosted deployment boundary

A successful cloud deployment does not widen an OnlyAsk authority envelope. Tool calls remain subject to the registered Strands capability boundary and mutating operations remain subject to the transition kernel.

Production deployments should use a dedicated least-privilege AWS execution role rather than developer or administrator credentials.

## Reporting

Please report security issues privately to the repository owner rather than opening a public exploit issue.
