# OnlyAsk v0.3 dogfood validation record

Date: 2026-08-25  
Branch: `dogfood-pwa-v0.3`  
Python runtime: 3.13.5

This record separates executed evidence from source review and from deployment work that still requires an external runtime.

## Scope of v0.3

v0.3 is not only a UI delta. It changes the governance core and therefore required a full Python regression pass.

Changes include:

- installable phone PWA;
- real GitHub dogfood adapter;
- constrained test runner;
- shared runtime-neutral capability gate;
- Strands adapter moved onto that common gate;
- experimental Rust/Rig 0.42 adapter consuming the same conformance fixture;
- explicit irreversible-transition semantics;
- `UNCERTAIN` state for irreversible outcomes that cannot be proven;
- read-only postcondition verification;
- exact tested-commit binding before phone merge approval.

## Exact source identity

The validation container cannot clone GitHub directly. Repository files were retrieved through the authenticated GitHub interface, reconstructed locally, and checked using Git's blob hashing rule.

The final security-sensitive blobs were byte-for-byte identical between GitHub and the executed tree, including:

- `src/onlyask/dogfood.py` — `984875f9ed8fd1149d26a268f814a54879a3dc3c`
- `tests/test_dogfood.py` — `b49d4ce08aa1aae4cbc74e3a1fbea64f4b0007ac`
- `src/onlyask/pwa.py` — `f2c7f2ae4c92c967fb9a20a98b525c8f002727e5`
- `tests/test_pwa.py` — `bec9dba0f84f7e64a295083b4f98baeaea7a2b5f`

The previously reconstructed authority, kernel, runtime-contract, GitHub adapter, Strands adapter, product, evaluation, and remaining test blobs were also included in the same local package graph.

## Full Python branch gate

Command equivalent:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
58 passed
```

The same tree also passed:

```bash
python -m compileall -q src tests agentcore_main.py
```

Result: **PASS**.

The 58-test suite includes the original product and governance tests plus v0.3 coverage for:

- delegated repository inspection and predefined tests;
- unknown runtime tools failing closed;
- transactional enforcement for mutating runtime tools;
- shared runtime conformance cases;
- explicit irreversible authority requiring a scoped human grant;
- exact parameter/grant widening resistance;
- stale PR head/base blocking execution;
- successful successor binding after merge;
- transport-error reconciliation when an irreversible successor is observable;
- `UNCERTAIN` when irreversible execution or verification cannot be proven;
- read-only postcondition verification;
- failed test runs reporting FAILED instead of VERIFIED;
- test evidence bound to an exact Git SHA;
- wrong GitHub origin rejection;
- dirty working-tree rejection;
- fixed no-shell runner commands;
- secret-free subprocess environment;
- PWA manifest/service-worker/icon shape;
- PWA authentication and derived session cookie;
- visible alarm styling for `UNCERTAIN` state.

## Deterministic governance evaluation

The current v0.3 authority engine and transition kernel were run through the deterministic evaluator after the core changes.

Result:

- scenarios: **11 / 11 passed**
- authority accuracy: **100%**
- unsafe allows: **0**
- unnecessary escalations: **0**
- observed human decisions matched expected human decisions
- all evaluated evidence ledgers: **valid**

This is current v0.3 evidence, not merely the historical v0.2 result.

## HTTP/PWA smoke gate

The PWA backend was started on loopback with a test-only PWA credential and local HTTP cookie override.

Observed:

| Check | Result |
| --- | --- |
| `GET /` | 200 |
| `GET /manifest.webmanifest` | 200 |
| `GET /sw.js` | 200 |
| generated icon | valid PNG |
| unauthenticated `GET /api/state` | 401 |
| incorrect login | 401 |
| correct login | 200 |
| cookie-authenticated state | 200 |
| manifest display | `standalone` |
| 192×192 + 512×512 icons | present |
| evidence ledger | valid |
| raw GitHub token in state response | absent |
| raw PWA token in state response | absent |
| non-loopback bind without PWA token | refused |

Production cookie behavior keeps `HttpOnly`, `SameSite=Strict`, and `Secure`. The backend also emits no-store, anti-sniffing, anti-framing, referrer, and CSP protections.

## DDC/security findings fixed during v0.3

The review produced code changes, not documentation-only findings:

1. **Head-only predecessor binding was insufficient.** Merge review now binds repository, PR number, head SHA, base branch, open/merged state, and exact action parameters.
2. **Approval reuse after stale/failure paths was possible.** An approval is one attempted transition and unused grant authority is revoked after an unsuccessful attempt.
3. **Post-merge verification was too weak.** Returned merge SHA must agree with the observed successor.
4. **Irreversible operations were modeled as fake-recoverable mutations.** They now require an exact scoped grant and become `UNCERTAIN` when reality cannot be reconciled.
5. **Read-only execution could be confused with successful outcome.** Non-mutating operations can now declare postconditions; failing pytest is FAILED, not VERIFIED.
6. **Test evidence could certify uncommitted code under the current HEAD SHA.** Merge-eligible test evidence now requires a clean working tree.
7. **A configured checkout could point at a different GitHub repository.** Runner evidence now requires the canonical origin to match the governed repository.
8. **Pytest inherited backend environment state.** The runner uses a small OS-variable allowlist and no GitHub/AWS/model-provider secrets.
9. **Browser token persistence was too permissive.** The PWA uses a derived `HttpOnly`, `SameSite=Strict` cookie rather than JavaScript storage.
10. **Ambiguous irreversible outcomes were visually too quiet.** `UNCERTAIN` now uses the phone alarm/error state styling.

## Rig 0.42 validation boundary

Implemented in `adapters/rig/`:

- pinned `rig = "=0.42.0"`;
- pre-tool `AgentHook` authority interception;
- invalid/unregistered tool fail-closed behavior;
- shared `conformance/runtime_adapter_cases.json` with the Python implementation;
- Rust unit tests for the common contract and resource mapping.

**Not yet executed:** Rust compilation and `cargo test`.

The validation container has no `cargo`/`rustc`, outbound package installation is blocked, Replit rejected creation of a temporary validator because the account requires an active subscription, and no authenticated Cloudflare Sandbox execution connector is available in this chat. No Replit project was created and no Replit credits were consumed.

Therefore the Rig source is **IMPLEMENTED / COMPILE GATE PENDING**. It must not be represented as a passing Rust test until `cargo test` has actually run on a Rust-capable host.

## Release status

- exact current Python full-suite gate: **PASS — 58/58**
- Python source/test/entrypoint compilation: **PASS**
- deterministic governance evaluation: **PASS — 11/11**
- HTTP/PWA smoke: **PASS**
- Rig 0.42 source/conformance implementation: **COMPLETE**
- Rig Rust compile/test: **PENDING — release blocker**
- real HTTPS phone deployment: **PENDING after code release gate**

v0.3 should remain on its branch/draft PR until the Rust compile/test gate is executed.
