from __future__ import annotations

import argparse

from .demo import run_demo


def main() -> None:
    parser = argparse.ArgumentParser(prog="onlyask")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="Run the deterministic governed-operations demo")

    evaluate = sub.add_parser("eval", help="Evaluate governed-autonomy behavior deterministically")
    evaluate.add_argument("--json", action="store_true", help="Emit the complete report as JSON")

    web = sub.add_parser("web", help="Run the interactive governed-operations console")
    web.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    web.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")

    agent = sub.add_parser("agent", help="Run the Strands-powered website operations agent")
    agent.add_argument(
        "prompt",
        nargs="*",
        help="Task for the agent; defaults to the end-to-end storefront repair scenario",
    )

    args = parser.parse_args()

    if args.command == "demo":
        print("OnlyAsk — Governed Autonomous Operations")
        for row in run_demo():
            print(f"{row['item']:<22} {row['result']}")
        return

    if args.command == "eval":
        from .evals import run_evaluations

        report = run_evaluations()
        if args.json:
            print(report.to_json())
            return

        summary = report.summary
        print("OnlyAsk — Deterministic Evaluation")
        print(
            f"cases {summary['passed_cases']}/{summary['total_cases']} | "
            f"authority accuracy {summary['authority_accuracy']:.0%} | "
            f"unsafe allows {summary['unsafe_allows']} | "
            f"unnecessary escalations {summary['unnecessary_escalations']}"
        )
        for case in report.cases:
            marker = "PASS" if case.passed else "FAIL"
            print(f"{marker:<4} {case.name:<48} {case.observed}")
        return

    if args.command == "web":
        from .webapp import serve

        serve(args.host, args.port)
        return

    if args.command == "agent":
        from .strands_product import build_site_agent

        prompt = " ".join(args.prompt).strip() or (
            "Inspect the storefront, repair the broken Contact link, then determine whether "
            "changing the primary plan price to $39.00 and changing DNS are permitted. "
            "Report verified outcomes and any human decision that is genuinely required."
        )
        strands_agent, _ = build_site_agent()
        print(strands_agent(prompt))


if __name__ == "__main__":
    main()
