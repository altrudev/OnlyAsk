from __future__ import annotations

import argparse

from .demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(prog="onlyask")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Run the deterministic governed-operations demo")
    args = parser.parse_args()

    if args.command == "demo":
        print("OnlyAsk — Governed Autonomous Operations")
        for row in run_demo():
            print(f"{row['item']:<22} {row['result']}")


if __name__ == "__main__":
    main()
