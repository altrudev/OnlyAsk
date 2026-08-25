# Security Policy

OnlyAsk is pre-1.0 research software. Do not deploy the reference code with broad production credentials.

## Principles

- grant the smallest tool and infrastructure permissions required
- keep secrets out of prompts, repositories, logs, browser storage, test output, and evidence records
- fail closed for unknown tools and unknown authority
- require verification and recovery for mutations where safe recovery exists
- bind authorized mutations to observed predecessor state when state drift is relevant
- never interpret retrieved content as a new authority source
- avoid unrestricted shell, arbitrary filesystem, and arbitrary outbound-network tools
- keep model reasoning separate from deterministic authority decisions
- treat hosting/runtime layers as execution infrastructure, not as authority sources
- do not commit credentials, access tokens, target state, or local environment files
- generate and review the dependency lockfile in a networked build environment before production deployment

## Dogfood PWA boundary

The v0.3 phone PWA is a control surface, not a credential store.

- `ONLYASK_GITHUB_TOKEN` remains in the backend process and is never returned by the PWA API.
- `ONLYASK_PWA_TOKEN` is a separate high-entropy phone-session secret. Browser login exchanges it for a derived `HttpOnly`, `SameSite=Strict` cookie; the original token is not stored in JavaScript storage.
- Remote phone use must be served through HTTPS. The session cookie is `Secure` by default.
- The GitHub adapter exposes named repository operations only. It does not expose a generic GitHub endpoint proxy.
- A requested merge is bound to the reviewed PR head, base branch, open/merged state, merge method, and exact action parameters.
- If the PR changes after review, the approved transition becomes stale and execution is blocked.
- A phone approval authorizes one attempted transition. A grant is revoked after a stale or failed attempt rather than remaining silently reusable.
- Successful merge verification binds the GitHub merge response SHA to the PR's observed merge commit SHA.
- The test runner invokes exactly `python -m pytest -q` without a shell and uses a sanitized environment that does not pass OnlyAsk, GitHub, AWS, model-provider, or other backend secrets into the test process.

### Test-code trust boundary

The current runner still executes Python test code from the configured local project checkout. A fixed command and sanitized environment reduce capability, but they do **not** make untrusted repository code safe. For now, configure `ONLYASK_PROJECT_ROOT` only for code you trust. A later release should move test execution into an OS/container sandbox with explicit filesystem, network, CPU, memory, and time limits before arbitrary third-party repositories are allowed.

## GitHub credential scope

Prefer a fine-grained token restricted to the specific dogfood repository. The current reference adapter needs repository read access for inspection and pull-request state, and `Contents: write` only when phone-approved PR merge execution is enabled. Do not use an account-wide classic token when a repository-scoped credential is sufficient.

## Hosted deployment boundary

A successful cloud deployment does not widen an OnlyAsk authority envelope. Infrastructure credentials make an operation technically possible; they do not make the operation authorized.

Production deployments should run the backend behind an authenticated HTTPS reverse proxy or equivalent edge and should add rate limiting, request-size limits, logging hygiene, and process isolation appropriate to the exposure level.

## Reporting

Please report security issues privately to the repository owner rather than opening a public exploit issue.
