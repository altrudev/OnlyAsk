# OnlyAsk v0.3 Dogfood PWA

The dogfood PWA turns OnlyAsk into a phone control surface for real development operations. The phone does not receive GitHub credentials and does not execute repository code itself. It talks to a backend that applies the OnlyAsk authority envelope before invoking a named adapter operation.

## v0.3 capability surface

### Automatic

- inspect the configured GitHub repository;
- list basic repository state and open pull requests;
- run the single predefined local test command `python -m pytest -q` in the configured trusted checkout;
- show recent governed operations and the evidence ledger.

### Human decision required

- merge a pull request into the configured default branch.

A merge request is assessed before it reaches the phone. Approval is exact and one-attempt only. The reviewed predecessor binds the PR head SHA, base branch, open/merged state, repository, PR number, and merge method. If that state changes before execution, the transition is `STALE` and the merge does not run.

### Not exposed / denied

The reference PWA does not expose repository deletion, force push, visibility changes, security-policy changes, arbitrary GitHub API calls, a generic filesystem writer, or a shell.

## Backend environment

The backend recognizes these variables:

| Variable | Purpose |
| --- | --- |
| `ONLYASK_PROJECT_ROOT` | Trusted local checkout used by the predefined pytest runner. |
| `ONLYASK_GITHUB_TOKEN` | Backend-only GitHub credential. Never returned to the PWA. |
| `ONLYASK_PWA_TOKEN` | Separate high-entropy secret used to establish the phone session. Required when binding beyond loopback. |
| `ONLYASK_SECURE_COOKIE` | Defaults to `1`. Set to `0` only for deliberate local HTTP debugging. |

Do not commit any of these values.

## GitHub credential

For dogfooding, prefer a fine-grained personal access token restricted to **only** `altrudev/OnlyAsk` rather than a classic account-wide token.

GitHub's current REST documentation says the pull-request read endpoint accepts `Pull requests: read` or `Contents: read`, while the synchronous merge endpoint requires `Contents: write`. The merge endpoint also accepts a `sha` parameter and rejects the merge if the PR head no longer matches it. OnlyAsk adds its own predecessor check before making that request and verifies the resulting merge commit afterward.

If you only want phone inspection at first, do not grant write permission. Enable `Contents: write` only when you are ready to test the governed merge path.

## Run on the backend machine

From a trusted checkout:

```bash
python -m venv .venv
# activate the environment for your OS
pip install -e '.[dev]'
pytest

# set ONLYASK_PROJECT_ROOT, ONLYASK_GITHUB_TOKEN and ONLYASK_PWA_TOKEN
onlyask pwa --host 127.0.0.1 --port 8787
```

Loopback is useful for desktop testing. A phone on another device cannot install the PWA from an ordinary `http://<LAN-IP>` origin because service workers/PWA installation require a secure context.

## Phone access

For a real phone test, put the backend behind HTTPS and proxy only to the local PWA port. Browsers allow service workers on HTTPS origins (and localhost for development), and Chromium installability expects the included manifest fields plus 192px and 512px icons.

Recommended deployment boundary:

```text
Phone
  |
  | HTTPS
  v
Authenticated / rate-limited edge or tunnel
  |
  v
OnlyAsk PWA backend
  |-- PWA session credential
  |-- GitHub credential (server only)
  |-- configured trusted checkout
  |
  +--> GitHub REST adapter
  +--> predefined test runner
```

Once the HTTPS origin is available, open it on the phone, sign in with the PWA session token, then use the browser's **Add to Home Screen / Install App** function.

## Merge authority flow

```text
Phone requests PR merge
        |
        v
OnlyAsk reads PR predecessor
        |
        v
No delegated merge authority
        |
        v
ESCALATE -> Decisions inbox
        |
   Approve once
        |
        v
Exact one-attempt grant
        |
        v
Re-read PR predecessor
   |              |
changed          same
   |              |
 STALE         GitHub merge
                  |
                  v
            verify successor SHA
                  |
            VERIFIED / failure
```

A stale or failed attempt revokes the one-time grant. Approval never becomes a reusable standing permission.

## Test runner trust boundary

`SafeTestRunner` is constrained but is not yet a sandbox. It:

- accepts no arbitrary command from the PWA;
- invokes pytest without `shell=True`;
- caps runtime and returned output;
- passes only a small allowlist of operating-system environment variables, so backend tokens and cloud/model credentials are not inherited.

However, Python tests are executable code and can still access the filesystem/network available to the backend process. v0.3 is therefore for **trusted dogfood repositories only**. Sandboxed execution is a planned next step before using this runner on untrusted projects.

## Current validation

The v0.3-specific test gate exercises:

- automatic repository inspection and test execution;
- exact one-time merge approval;
- PR-head drift blocking;
- PR-base retarget blocking;
- successor merge-commit binding;
- approval revocation after a stale attempt;
- explicit human rejection evidence;
- endpoint-injection rejection;
- fixed no-shell pytest invocation;
- backend-secret stripping from the test process;
- PWA manifest/icon generation;
- PWA authentication and derived session cookie.

See `docs/VALIDATION_V03.md` for the executed-validation boundary.
