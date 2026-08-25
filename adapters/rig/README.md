# OnlyAsk Rig adapter

This crate adapts Rig 0.42.x tool-call hooks to the OnlyAsk authority contract.

It is intentionally **not** a new authority source. The adapter has two jobs:

1. intercept Rig tool dispatch before execution and map the call into ALLOW / ESCALATE / DENY;
2. prove compatibility with the same conformance fixture used by the Python reference implementation in `conformance/runtime_adapter_cases.json`.

The authoritative state transition still belongs to the OnlyAsk transactional tool implementation. A Rig hook allowing a mutating tool means only that the tool is inside the registered capability surface; the tool itself must still use the OnlyAsk transition kernel for predecessor binding, scoped grants, verification, recovery, or explicit irreversible-transition handling.

## Rig version

The crate pins the public `rig` facade to `=0.42.0`. That version uses event-specific `AgentHook` methods. `on_tool_call` runs before a valid tool executes and can return `ToolCallAction::skip(...)` to prevent execution. `on_invalid_tool_call` is also implemented so an invalid or unregistered model-emitted tool call is skipped rather than repaired into a broader capability.

Sensitive content telemetry should remain at Rig's default (`false`) unless an operator explicitly decides otherwise.

## Use

Attach `OnlyAskRigHook` with Rig's normal hook registration (`add_hook`) after constructing a gate for the exact tool surface. Do not register generic shell, arbitrary filesystem writer, or arbitrary network proxy tools merely because the hook exists.

## Conformance

From this directory, with a Rust toolchain and network/cache access for the pinned dependencies:

```bash
cargo test --locked
```

If no `Cargo.lock` exists yet, run `cargo test` once in a trusted development environment, review the resolved dependency graph, commit the resulting lockfile, and rerun with `--locked`.

The tests load `../../conformance/runtime_adapter_cases.json` directly, so Python and Rust cannot silently drift onto different expected decisions.

## Current validation boundary

The ChatGPT execution runtime used for v0.3 has Python 3.13 but no `cargo`, `rustc`, or outbound package installation. The source has therefore been aligned to the current Rig 0.42 public API documentation, but Rust compilation must remain marked pending until it is executed on a Rust-capable host. Do not treat source review as a compile pass.
