from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from onlyask.strands_product import build_site_agent


app = BedrockAgentCoreApp()
agent, session = build_site_agent()


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Amazon Bedrock AgentCore Runtime entry point for the OnlyAsk Strands agent."""

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "'prompt' must be a non-empty string"}

    response = agent(prompt.strip())
    state = session.state()
    return {
        "response": str(response),
        "onlyask": {
            "pending_human_decisions": state["pending"],
            "metrics": state["metrics"],
            "ledger_valid": state["ledger_valid"],
        },
    }


if __name__ == "__main__":
    app.run()
