import json

from models.ai import PendingAction
from models.task import Task
from services.ai import agent
from services.ai.llm import LLMError


class FakeClient:
    """Stands in for the real LLM. Never makes a network call."""

    def __init__(self, responses, configured=True):
        self.responses = list(responses)
        self.configured = configured
        self.calls = []

    def is_configured(self):
        return self.configured

    def chat(self, messages, tools=None):
        self.calls.append({"messages": list(messages), "tools": tools})
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def call(name, args=None, cid="c1"):
    return {"id": cid, "name": name, "arguments": {} if args is None else args}


def reply(text):
    return {"content": text, "tool_calls": []}


def tools_reply(*calls):
    return {"content": "", "tool_calls": list(calls)}


def test_no_api_key_gives_honest_setup_message_and_no_fake_answer(app, data):
    c = FakeClient([], configured=False)
    r = agent.run_agent(data["admin_ctx"], "How much did I spend?", client=c)
    assert r["ok"] is False and r["error"] == "not_configured"
    assert "AI_API_KEY" in r["reply"]
    assert c.calls == []  # the model was never called


def test_read_tool_result_is_passed_back_to_model(app, data):
    c = FakeClient([tools_reply(call("get_inventory_alerts")), reply("Urea is low.")])
    r = agent.run_agent(data["admin_ctx"], "What is low?", client=c)
    assert r["ok"] and r["reply"] == "Urea is low."
    assert r["tool_activity"][0]["status"] == "ok"
    tool_msg = [m for m in c.calls[1]["messages"] if m["role"] == "tool"][0]
    assert "Urea" in tool_msg["content"]          # grounded in real DB data


def test_write_tool_only_creates_proposal(app, data):
    before = Task.query.count()
    args = {"title": "Spray check", "due_date": data["today"].isoformat(), "priority": "Low"}
    c = FakeClient([tools_reply(call("create_farm_task", args)), reply("Proposed. Please approve.")])
    r = agent.run_agent(data["admin_ctx"], "Add a task", client=c)
    assert Task.query.count() == before
    assert len(r["pending_actions"]) == 1 and r["pending_actions"][0]["status"] == "pending"
    assert r["tool_activity"][0]["status"] == "pending_confirmation"
    assert PendingAction.query.count() == 1


def test_invalid_tool_args_are_reported_to_model_not_executed(app, data):
    c = FakeClient([tools_reply(call("create_farm_task", {"title": "x", "due_date": "bad"})), reply("Sorry.")])
    r = agent.run_agent(data["admin_ctx"], "Add a task", client=c)
    assert r["pending_actions"] == [] and r["tool_activity"][0]["status"] == "error"
    assert PendingAction.query.count() == 0


def test_worker_cannot_reach_admin_tool_via_model(app, data):
    c = FakeClient([tools_reply(call("get_expense_summary")), reply("Not allowed.")])
    r = agent.run_agent(data["w1_ctx"], "How much did we spend?", client=c)
    assert r["tool_activity"][0]["status"] == "denied"
    tool_msg = [m for m in c.calls[1]["messages"] if m["role"] == "tool"][0]
    assert "permission" in tool_msg["content"]
    assert "get_expense_summary" not in json.dumps(c.calls[0]["tools"])   # not even offered


def test_unknown_tool_and_bad_json_arguments(app, data):
    bad = {"id": "c2", "name": "get_pending_tasks", "arguments": None}
    c = FakeClient([tools_reply(call("run_shell", {"cmd": "ls"}), bad), reply("done")])
    r = agent.run_agent(data["admin_ctx"], "hi", client=c)
    assert [a["status"] for a in r["tool_activity"]] == ["error", "error"]


def test_max_steps_is_enforced(app, data):
    app.config["AI_MAX_STEPS"] = 3
    c = FakeClient([tools_reply(call("get_pending_tasks")) for _ in range(10)])
    r = agent.run_agent(data["admin_ctx"], "loop forever", client=c)
    assert r["error"] == "max_steps" and len(c.calls) == 3


def test_llm_failure_returns_helpful_fallback(app, data):
    c = FakeClient([LLMError("The AI service took too long to respond. Please try again.")])
    r = agent.run_agent(data["admin_ctx"], "hi", client=c)
    assert r["ok"] is False and r["error"] == "llm_error"
    assert "took too long" in r["reply"] and "quick data buttons" in r["reply"]


def test_tool_crash_is_not_leaked(app, data, monkeypatch):
    from services.ai import tools
    def boom(ctx, args):
        raise RuntimeError("secret internal detail /etc/passwd")
    monkeypatch.setitem(tools.REGISTRY, "get_pending_tasks",
                        tools.Tool("get_pending_tasks", "x", "x", tools._EMPTY, tools._no_args, boom, ("admin", "worker")))
    c = FakeClient([tools_reply(call("get_pending_tasks")), reply("ok")])
    agent.run_agent(data["admin_ctx"], "hi", client=c)
    tool_msg = [m for m in c.calls[1]["messages"] if m["role"] == "tool"][0]
    assert "secret internal detail" not in tool_msg["content"]


def test_system_prompt_contains_safety_rules(app, data):
    c = FakeClient([reply("hi")])
    agent.run_agent(data["admin_ctx"], "hi", client=c)
    system = c.calls[0]["messages"][0]["content"]
    assert "Never invent" in system and "PROPOSAL" in system and "irrigation equipment" in system
