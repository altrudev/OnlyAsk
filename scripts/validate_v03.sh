#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

printf '\n== OnlyAsk v0.3 release validation ==\n'
printf 'repo: %s\n' "$ROOT"
printf 'head: %s\n' "$(git rev-parse HEAD)"
printf 'branch: %s\n' "$(git branch --show-current)"

if [[ -n "$(git status --porcelain=v1)" ]]; then
  echo 'ERROR: working tree is not clean. Commit/stash changes before validating.' >&2
  git status --short >&2
  exit 2
fi

origin="$(git remote get-url origin)"
printf 'origin: %s\n' "$origin"
case "$origin" in
  https://github.com/altrudev/OnlyAsk|https://github.com/altrudev/OnlyAsk.git|git@github.com:altrudev/OnlyAsk.git|ssh://git@github.com/altrudev/OnlyAsk.git)
    ;;
  *)
    echo 'ERROR: origin is not the canonical altrudev/OnlyAsk repository.' >&2
    exit 3
    ;;
esac

printf '\n== Python ==\n'
python --version
python -m pip install --disable-pip-version-check 'pytest>=8.2'
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m onlyask.cli eval
python -m compileall -q src tests agentcore_main.py

printf '\n== Rust / Rig ==\n'
if ! command -v cargo >/dev/null 2>&1; then
  echo 'ERROR: cargo is not installed. Install the Rust toolchain, then rerun.' >&2
  exit 4
fi
cargo --version
rustc --version

if command -v rustfmt >/dev/null 2>&1; then
  cargo fmt --manifest-path adapters/rig/Cargo.toml -- --check
else
  echo 'NOTE: rustfmt not installed; format check skipped.'
fi

cargo test --manifest-path adapters/rig/Cargo.toml
cargo test --manifest-path adapters/rig/Cargo.toml --locked

if command -v cargo-clippy >/dev/null 2>&1; then
  cargo clippy --manifest-path adapters/rig/Cargo.toml --all-targets -- -D warnings
else
  echo 'NOTE: clippy not installed; lint gate skipped.'
fi

printf '\nPASS: OnlyAsk v0.3 Python and Rig release validation completed.\n'
printf 'Cargo.lock should now exist under adapters/rig and must be reviewed/committed before merge.\n'
