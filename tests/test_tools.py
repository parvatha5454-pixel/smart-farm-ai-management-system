import pytest

from models import db
from models.ai import AuditLog, PendingAction
from models.task import Task
from services.ai import actions
from services.ai.tools import REGISTRY, UserCtx, openai_tool_specs, prepare_call, run_tool
from services.ai.validation import ToolError


def test_expense_summary_totals_and_range(data):
    r = run_tool("get_expense_summary", {"start_date": "2025-01-01", "end_date": "2025-01-31"}, data["admin_ctx"])
    assert r["total_spent"] == 350.5          # 100 + 50.5 + 200; boundary dates included
    assert r["number_of_expenses"] == 3
    cats = {c["category"]: c["total"] for c in r["by_category"]}
    assert cats == {"Labour": 200.0, "Seeds": 150.5}
    assert r["by_category"][0]["category"] == "Labour"  # sorted by amount desc


def test_expense_summary_empty_range(data):
    r = run_tool("get_expense_summary", {"start_date": "2020-01-01", "end_date": "2020-01-31"}, data["admin_ctx"])
    assert r["total_spent"] == 0 and r["number_of_expenses"] == 0 and r["by_category"] == []


@pytest.mark.parametrize("args", [
    {"start_date": "2025-02-01", "end_date": "2025-01-01"},
    {"start_date": "not-a-date"},
    {"start_date": "2025-01-01", "extra": "x"},
    {"start_date": "1990-01-01", "end_date": "2025-01-01"},
])
def test_expense_summary_invalid_input(data, args):
    with pytest.raises(ToolError):
        run_tool("get_expense_summary", args, data["admin_ctx"])


def test_pending_tasks_admin_sees_all_open(data):
    r = run_tool("get_pending_tasks", {}, data["admin_ctx"])
    titles = {t["title"] for t in r["tasks"]}
    assert titles == {"Water tomatoes", "Old task", "Other worker task"}   # completed excluded
    assert r["open_tasks"] == 3 and r["overdue_tasks"] == 1


def test_pending_tasks_worker_sees_only_own(data):
    r = run_tool("get_pending_tasks", {}, data["w1_ctx"])
    assert {t["title"] for t in r["tasks"]} == {"Water tomatoes", "Old task"}


def test_pending_tasks_worker_without_profile(data):
    r = run_tool("get_pending_tasks", {}, UserCtx(99999, "worker"))
    assert r["tasks"] == []


def test_inventory_alerts(data):
    r = run_tool("get_inventory_alerts", {}, data["w1_ctx"])
    assert [i["name"] for i in r["items"]] == ["Urea"]
    assert r["items"][0]["shortfall"] == 8
    assert r["items_without_minimum_level"] == 1


def test_field_and_crop_details_admin_and_worker(data):
    a = run_tool("get_field_and_crop_details", {}, data["admin_ctx"])
    north = [f for f in a["fields"] if f["name"] == "North"][0]
    assert {c["name"] for c in north["crops"]} == {"Tomato", "Chilli"}
    assert a["fields_without_crops"] == ["South"]
    w = run_tool("get_field_and_crop_details", {}, data["w1_ctx"])
    assert "fields" not in w and {c["name"] for c in w["crops"]} == {"Tomato", "Chilli"}


def test_farm_summary_counts(data):
    r = run_tool("get_farm_summary", {}, data["admin_ctx"])
    assert r["total_fields"] == 2 and r["total_crops"] == 2 and r["total_workers"] == 2
    assert r["open_tasks"] == 3 and r["overdue_tasks"] == 1 and r["low_stock_items"] == 1


# ---- permissions
@pytest.mark.parametrize("tool", ["get_farm_summary", "get_expense_summary", "generate_weekly_farm_plan"])
def test_worker_cannot_use_admin_tools(data, tool):
    with pytest.raises(ToolError) as e:
        run_tool(tool, {}, data["w1_ctx"])
    assert e.value.code == "forbidden"


def test_worker_gets_no_write_tool_in_specs(data):
    assert "create_farm_task" not in [s["function"]["name"] for s in openai_tool_specs("worker")]
    assert "create_farm_task" in [s["function"]["name"] for s in openai_tool_specs("admin")]


def test_unknown_tool_and_no_user(data):
    with pytest.raises(ToolError):
        run_tool("run_sql", {"query": "DROP TABLE tasks"}, data["admin_ctx"])
    with pytest.raises(ToolError):
        prepare_call("get_pending_tasks", {}, None)


def test_every_registered_tool_rejects_unexpected_params(data):
    for name, tool in REGISTRY.items():
        with pytest.raises(ToolError):
            prepare_call(name, {"sql": "SELECT 1"}, data["admin_ctx"])


# ---- write tools / confirmation
def test_create_task_without_confirmation_is_blocked(data):
    with pytest.raises(ToolError) as e:
        run_tool("create_farm_task", {"title": "X", "due_date": data["today"].isoformat()}, data["admin_ctx"])
    assert e.value.code == "confirmation_required"
    assert Task.query.filter_by(title="X").count() == 0


def test_proposal_does_not_change_tasks(data):
    before = Task.query.count()
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Fix fence", "due_date": data["today"].isoformat(), "priority": "high"})
    assert a.status == "pending" and Task.query.count() == before
    assert AuditLog.query.filter_by(event="ai_proposed").count() == 1


def test_confirm_creates_task_and_audits(data):
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Fix fence", "due_date": data["today"].isoformat(), "priority": "High"})
    actions.confirm_action(a.id, data["admin_ctx"])
    t = Task.query.filter_by(title="Fix fence").one()
    assert t.priority == "High" and t.status == "Pending" and t.worker_id is None
    assert db.session.get(PendingAction, a.id).status == "approved"
    events = {l.event for l in AuditLog.query.all()}
    assert {"ai_proposed", "user_approved", "executed"} <= events


def test_cannot_confirm_twice_or_someone_elses_proposal(data):
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Once", "due_date": data["today"].isoformat()})
    other_admin = UserCtx(12345, "admin", "Other")
    with pytest.raises(ToolError) as e:
        actions.confirm_action(a.id, other_admin)
    assert e.value.code == "not_found"
    actions.confirm_action(a.id, data["admin_ctx"])
    with pytest.raises(ToolError) as e:
        actions.confirm_action(a.id, data["admin_ctx"])
    assert e.value.code == "already_resolved"
    assert Task.query.filter_by(title="Once").count() == 1


def test_reject_saves_nothing(data):
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Nope", "due_date": data["today"].isoformat()})
    actions.reject_action(a.id, data["admin_ctx"])
    assert Task.query.filter_by(title="Nope").count() == 0
    assert db.session.get(PendingAction, a.id).status == "rejected"


def test_permissions_rechecked_at_confirmation(data):
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Demoted", "due_date": data["today"].isoformat()})
    demoted = UserCtx(data["admin_ctx"].id, "worker", "Owner")   # role changed after proposal
    with pytest.raises(ToolError) as e:
        actions.confirm_action(a.id, demoted)
    assert e.value.code == "forbidden"
    assert Task.query.filter_by(title="Demoted").count() == 0
    assert db.session.get(PendingAction, a.id).status == "failed"


def test_worker_cannot_propose(data):
    with pytest.raises(ToolError) as e:
        actions.propose_action(data["w1_ctx"], "create_farm_task",
                               {"title": "X", "due_date": data["today"].isoformat()})
    assert e.value.code == "forbidden"


@pytest.mark.parametrize("args", [
    {"title": "", "due_date": "2999-01-01"},
    {"title": "ok", "due_date": "2000-01-01"},
    {"title": "ok", "due_date": "garbage"},
    {"title": "ok", "due_date": "TODAY", "priority": "Medium"},
])
def test_invalid_task_proposals_rejected(data, args):
    with pytest.raises(ToolError):
        actions.propose_action(data["admin_ctx"], "create_farm_task", args)
    assert PendingAction.query.count() == 0


def test_weather_tool_without_location_is_honest(data):
    r = run_tool("get_weather_forecast", {}, data["admin_ctx"])
    assert r["available"] is False and "FARM_LOCATION" in r["reason"]
