from __future__ import annotations

import argparse

from .demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(prog="onlyask")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Run the deterministic governed-operations demo")

    web = sub.add_parser("web", help="Run the interactive governed-operations console")
    web.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    web.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")

    args = parser.parse_args()

    if args.command == "demo":
        print("OnlyAsk — Governed Autonomous Operations")
        for row in run_demo():
            print(f"{row['item']:<22} {row['result']}")
        return

    if args.command == "web":
        from .webapp import serve

        serve(args.host, args.port)


if __name__ == "__main__":
    main()
