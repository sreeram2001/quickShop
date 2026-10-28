# The file that calls the Strands harness.
from strands_harness import create_harness

from quickshop.agent.hooks import TraceLogger
from quickshop.agent.interventions import CreditBudget
from quickshop.agent.prompts import build_instructions
from quickshop.config import build_model
from quickshop.tools import DEFAULT_TOOLS

def build_agent(tools=None, credits=5, session_id=None, model=None):
    # tools and model can be swapped.
    if tools is None:
        tools = DEFAULT_TOOLS
    if model is None:
        model = build_model()
    budget = CreditBudget(credits)
    trace = TraceLogger()
    agent = create_harness(
        model=model,
        instructions=build_instructions(credits),
        tools=tools,
        builtin_tools=[], # set no shell, file or web tools
        builtin_plugins=[],
        skills=False,
        memory=False,
        background_tasks=False,
        # Sessions are saved to disk, and the user's size and height would be saved too.
        # It's off unless a session_id is given.
        session={"id": session_id, "dir": ".sessions"} if session_id else False,
        interventions=[budget],
        hooks=[trace],
    )
    # the caller can read the budget and the trace after a run
    agent.budget = budget
    agent.trace = trace
    return agent
