# Strands Integration

OnlyAsk uses Strands as the agent reasoning/tool-selection layer while keeping authority enforcement outside model prompting.

The reference adapter uses `BeforeToolCallEvent`, which Strands emits immediately before tool execution. A registered policy maps each tool to a resource namespace and operation. Unregistered tools fail closed.

```python
from strands import Agent, tool

from onlyask.ledger import EvidenceLedger
from onlyask.models import AuthorityEnvelope, Permission
from onlyask.strands_adapter import StrandsAuthorityHook, ToolPolicy

@tool
def inspect_page(url: str) -> str:
    """Inspect a page."""
    return "..."

envelope = AuthorityEnvelope(
    objective="Inspect and repair the demo website",
    allow=[Permission("website/*", "read")],
    deny=[Permission("credentials/*", "*")],
)
ledger = EvidenceLedger()

agent = Agent(tools=[inspect_page])
StrandsAuthorityHook(
    envelope,
    policies={
        "inspect_page": ToolPolicy(
            resource_from_input=lambda p: f"website/{p['url']}",
            operation="read",
            mutating=False,
        )
    },
    ledger=ledger,
).register(agent)
```

When a ledger is supplied, every pre-tool authority decision is appended as `strands_tool_authority_decision`. That includes allowed invocations as well as fail-closed cases such as unregistered tools and mutating tools that lack transactional enforcement. In the v0.2 product agent the hook and `TransitionKernel` share the same ledger, giving the console one evidence chain from model-selected tool boundary through verified state transition.

For mutating tools, the hook is the first execution boundary, not the whole transaction. Mutating policies are denied unless they are explicitly marked `transactional=True`, and such a tool must invoke `TransitionKernel` so predecessor-state checks, verification, recovery, scoped-grant consumption, and transition evidence remain mandatory. The flag is an integration assertion, not a substitute for code review.

## Product agent

The competition product agent is built by `onlyask.strands_product.build_site_agent()` and can be invoked from the CLI:

```bash
pip install -e '.[strands]'
onlyask agent
```

The reference scenario exposes deliberately narrow tools for homepage inspection/repair, a commercial-change request, external-content inspection, and a DNS-change attempt. No generic shell or arbitrary writer is registered.

The commercial-change tool is intentionally an **authority-query surface** at the Strands boundary: calling it is non-mutating, while the proposed commerce write is evaluated by `TransitionKernel`. If the write is outside delegated authority, the kernel creates a pending human decision rather than granting the model write access.

## Security rule

Do not expose an unrestricted shell, arbitrary filesystem write, or arbitrary network tool and rely on the model to self-police. Tool registration is an explicit capability surface, and model prompting is not an enforcement boundary.
