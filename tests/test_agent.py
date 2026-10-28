# These tests run offline. They never call the model or any API.
from types import SimpleNamespace

from quickshop.agent.hooks import TraceLogger
from quickshop.agent.interventions import CreditBudget
from quickshop.agent.orchestrator import build_agent
from quickshop.tools import DEFAULT_TOOLS

FIVE_TOOLS = {
    "search_listings",
    "check_merchant",
    "fetch_product_evidence",
    "score_product",
    "ask_user",
}

def test_agent_has_only_our_five_tools_and_retrieve_context(monkeypatch):
    monkeypatch.setenv("API_KEY", "test")
    agent = build_agent()
    # retrieve_context comes from the harness context manager, it only reads saved tool results
    assert set(agent.tool_names) == FIVE_TOOLS | {"retrieve_context"}

def test_no_shell_or_file_tools(monkeypatch):
    monkeypatch.setenv("API_KEY", "test")
    agent = build_agent()
    for bad in ["shell", "read", "write", "edit", "web_fetch", "web_search", "subagent"]:
        assert bad not in agent.tool_names

def test_default_tools_match_the_five_names():
    names = {t.tool_name for t in DEFAULT_TOOLS}
    assert names == FIVE_TOOLS

def test_budget_blocks_the_extra_page_read():
    budget = CreditBudget(credits=2)
    read = SimpleNamespace(tool_use={"name": "fetch_product_evidence"})
    results = [type(budget.before_tool_call(read)).__name__ for _ in range(3)]
    assert results == ["Proceed", "Proceed", "Deny"]

def test_budget_ignores_cheap_tools():
    budget = CreditBudget(credits=0)
    search = SimpleNamespace(tool_use={"name": "search_listings"})
    assert type(budget.before_tool_call(search)).__name__ == "Proceed"

def test_budget_resets_for_a_new_request():
    budget = CreditBudget(credits=1)
    read = SimpleNamespace(tool_use={"name": "fetch_product_evidence"})
    budget.before_tool_call(read)
    budget.before_invocation(SimpleNamespace())
    assert type(budget.before_tool_call(read)).__name__ == "Proceed"

def test_trace_logger_records_a_call():
    trace = TraceLogger()
    event = SimpleNamespace(
        tool_use={"name": "search_listings", "input": {"query": "jeans"}},
        result={"status": "success"},
        cancel_message=None,
    )
    trace.log(event)
    assert trace.calls == [
        {
            "tool": "search_listings",
            "input": {"query": "jeans"},
            "status": "success",
            "blocked": False,
        }
    ]
