# An intervention can stop a tool call before it runs. This limits the costly page reads.
from strands.interventions import Deny, InterventionHandler, Proceed

COSTLY_TOOLS = {"fetch_product_evidence"}

class CreditBudget(InterventionHandler):
    name = "credit-budget"

    def __init__(self, credits=5):
        self.credits = credits
        self.used = 0

    def before_invocation(self, event, **kwargs):
        # a new user request starts with a full budget
        self.used = 0
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        if event.tool_use["name"] not in COSTLY_TOOLS:
            return Proceed()
        if self.used >= self.credits:
            return Deny(reason=f"Budget used up ({self.credits} page reads). "
                               "Do not read more pages. Decide with the evidence you have.")
        self.used += 1
        return Proceed()
