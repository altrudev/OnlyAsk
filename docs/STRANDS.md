# Strands Integration

OnlyAsk uses Strands as the agent reasoning/tool-selection layer while keeping authority enforcement outside model prompting.

The reference adapter uses `BeforeToolCallEvent`, which Strands emits immediately before tool execution. A registered policy maps each tool to a resource namespace and operation. Unregistered tools fail closed.

```python
from strands import Agent, tool

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
).register(agent)
```

For mutating tools, the hook is the first execution boundary, not the whole transaction. The tool implementation should invoke `TransitionKernel` so state-drift checks, verification, recovery, scoped-grant consumption, and ledger evidence remain mandatory.

## Security rule

Do not expose an unrestricted shell, arbitrary filesystem write, or arbitrary network tool and rely on the model to self-police. Tool registration is an explicit capability surface.
