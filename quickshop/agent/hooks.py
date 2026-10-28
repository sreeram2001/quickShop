# A hook runs after something happens. This writes every tool call
# so our check can count them later.
from strands.hooks import AfterToolCallEvent, HookProvider

class TraceLogger(HookProvider):
    def __init__(self):
        self.calls = []

    def register_hooks(self, registry, **kwargs):
        registry.add_callback(AfterToolCallEvent, self.log)

    def log(self, event):
        self.calls.append({
            "tool": event.tool_use["name"],
            "input": event.tool_use["input"],
            "status": event.result["status"],
            "blocked": event.cancel_message is not None,
        })
