# OnlyAsk v0.3 dogfood validation record

Date: 2026-08-25  
Branch: `dogfood-pwa-v0.3`  
Runtime: Python 3.13.5

This record separates what was actually executed from historical v0.2 evidence and from deployment steps that still require a real hosted backend.

## Exact source identity

The local validation runtime cannot clone GitHub directly. The v0.3 files were therefore retrieved through the authenticated GitHub repository interface, reconstructed locally, and checked using Git's blob hashing rule before execution.

The executed v0.3-relevant package graph included exact repository blobs for:

- `src/onlyask/__init__.py`
- `src/onlyask/authority.py`
- `src/onlyask/models.py`
- `src/onlyask/kernel.py`
- `src/onlyask/ledger.py`
- `src/onlyask/directives.py`
- `src/onlyask/product.py`
- `src/onlyask/github_adapter.py`
- `src/onlyask/dogfood.py`
- `src/onlyask/pwa.py`
- `tests/test_dogfood.py`
- `tests/test_github_adapter.py`
- `tests/test_pwa.py`

The final GitHub adapter blob used the current GitHub REST API version `2026-03-10`.

## v0.3-specific pytest gate

Command equivalent:

```bash
PYTHONPATH=src pytest -q \
  tests/test_dogfood.py \
  tests/test_github_adapter.py \
  tests/test_pwa.py
```

Result:

```text
11 passed
```

Covered behavior:

1. configured repository inspection runs inside delegated read authority;
2. the fixed test operation runs without a human escalation;
3. PR merge requires a human decision;
4. approval is exact and one-use;
5. reviewed PR head drift produces `STALE` and prevents merge;
6. PR retargeting to a different base after review also produces `STALE`;
7. a stale attempt revokes the remaining scoped grant;
8. successful merge verification binds the merge response SHA to the PR's observed merge commit SHA;
9. explicit human rejection is written to the evidence ledger;
10. repository-name validation rejects endpoint-injection input;
11. the runner uses a fixed no-shell pytest command and does not inherit backend GitHub/AWS/model-provider secrets;
12. the PWA manifest contains the installability fields and required icon sizes;
13. generated icons have valid PNG signatures;
14. PWA authentication rejects bad credentials and accepts the derived session cookie without storing the original token in JavaScript.

Several of these properties are combined into single pytest cases; the test count is 11.

## Compilation

The exact v0.3-relevant source/test tree was compiled with Python's bytecode compiler.

Result: **PASS**.

## HTTP/PWA smoke gate

The exact PWA source was started on loopback with a test-only 32-character PWA session token and `ONLYASK_SECURE_COOKIE=0` for local HTTP debugging.

Observed endpoints:

| Check | Result |
| --- | --- |
| `GET /` | 200 |
| `GET /manifest.webmanifest` | 200 |
| `GET /sw.js` | 200 |
| `GET /icon-192.png` | 200, valid PNG signature |
| unauthenticated `GET /api/state` | 401 |
| bad `POST /api/login` | 401 |
| valid `POST /api/login` | 200 |
| cookie-authenticated `GET /api/state` | 200 |
| manifest display mode | `standalone` |
| manifest icons | 192x192 and 512x512 |
| evidence ledger state | valid |
| raw GitHub token exposed by state API | no |

The login response set a derived `oa_session` cookie with `HttpOnly` and `SameSite=Strict`. Production/phone use keeps `Secure` enabled and therefore requires HTTPS.

## DDC/security findings fixed during the pass

The implementation was changed during review rather than merely documented:

- **head-only predecessor binding was insufficient**: the PR predecessor now binds head SHA, base branch, open/merged state, repository/PR identity, and action parameters, so retargeting after review invalidates approval;
- **approval reuse after a failed attempt was possible**: a phone approval is now one attempted transition; stale/failure paths revoke the unused grant;
- **post-merge verification was too weak**: the GitHub merge response SHA must now match the observed PR merge commit SHA;
- **pytest inherited backend environment state**: the runner now receives a small OS-variable allowlist and no OnlyAsk/GitHub/AWS/model-provider secrets;
- **browser token persistence was too permissive**: the PWA uses a derived `HttpOnly`, `SameSite=Strict` session cookie rather than JavaScript local storage;
- **REST version pin was old but still supported**: the adapter now pins GitHub REST API `2026-03-10`.

## Historical v0.2 regression evidence

The v0.2 deterministic release gate was previously executed against exact repository blobs and passed **25 / 25 tests**, plus **11 / 11 governance evaluation scenarios** with 0 unsafe allows and 0 unnecessary escalations.

The v0.3 branch does not modify the v0.2 authority engine, transition kernel, ledger, directive classifier, product scenario, evaluation harness, Strands authority adapter, or their existing tests. Their Git blob identities remain unchanged.

Because this validation runtime cannot clone the complete GitHub tree directly, this record does **not** relabel the historical 25/25 run plus the new 11/11 run as a single 36-test pytest invocation. A clone-capable deployment host should run the complete repository suite before the v0.3 PR is merged.

## Remaining deployment gate

A phone cannot install the PWA from a normal HTTP LAN address. The next gate is a real HTTPS backend with:

- a trusted OnlyAsk checkout;
- `ONLYASK_PROJECT_ROOT`;
- a repository-scoped GitHub credential;
- a separate high-entropy `ONLYASK_PWA_TOKEN`;
- HTTPS/reverse-proxy or tunnel termination;
- rate limiting and appropriate process isolation.

The current pytest runner is for trusted dogfood code only. It is constrained but not an OS/container sandbox.

## Current release status

- v0.3 dogfood-specific exact-blob gate: **PASS (11/11)**
- v0.3 HTTP/PWA smoke gate: **PASS**
- v0.2 unchanged regression evidence: **PASS (historical exact 25/25 + 11/11 evals)**
- complete repository pytest on clone-capable host: **PENDING**
- real HTTPS phone deployment: **PENDING**
