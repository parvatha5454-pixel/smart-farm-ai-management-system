from models.ai import PendingAction
from models.task import Task
from services.ai import actions
from tests.helpers import login


def test_copilot_requires_login(client_factory):
    c = client_factory()
    assert c.get("/copilot").status_code == 302
    assert c.post("/copilot/chat", json={"message": "hi"}).status_code == 302


def test_copilot_page_shows_honest_setup_message_without_key(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.get("/copilot").get_data(as_text=True)
    assert "AI chat is not set up" in html and "Quick data" in html


def test_chat_without_key_returns_setup_message_not_fake_answer(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    r = c.post("/copilot/chat", json={"message": "How much did I spend?"}).get_json()
    assert r["ok"] is False and r["error"] == "not_configured"


def test_chat_rejects_empty_and_oversized_messages(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    assert c.post("/copilot/chat", json={"message": "   "}).status_code == 400
    assert c.post("/copilot/chat", json={"message": "x" * 1001}).status_code == 400
    assert c.post("/copilot/chat", data="not json").status_code == 400


def test_quick_tool_works_without_ai(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    r = c.post("/copilot/quick/get_inventory_alerts", json={}).get_json()
    assert r["ok"] and r["data"]["items"][0]["name"] == "Urea"


def test_quick_tool_enforces_roles_and_blocks_write_tools(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    assert c.post("/copilot/quick/get_expense_summary", json={}).status_code == 403
    assert c.post("/copilot/quick/create_farm_task", json={"args": {}}).status_code == 404
    assert c.post("/copilot/quick/run_sql", json={}).status_code == 404


def test_confirm_endpoint_creates_task(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Via route", "due_date": data["today"].isoformat()})
    r = c.post("/copilot/actions/%d/confirm" % a.id)
    assert r.status_code == 200 and r.get_json()["ok"]
    assert Task.query.filter_by(title="Via route").count() == 1
    assert c.post("/copilot/actions/%d/confirm" % a.id).status_code == 409   # no double-save


def test_reject_endpoint_saves_nothing(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Rejected one", "due_date": data["today"].isoformat()})
    assert c.post("/copilot/actions/%d/reject" % a.id).status_code == 200
    assert Task.query.filter_by(title="Rejected one").count() == 0


def test_worker_cannot_confirm_admins_proposal(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    a = actions.propose_action(data["admin_ctx"], "create_farm_task",
                               {"title": "Admin only", "due_date": data["today"].isoformat()})
    assert c.post("/copilot/actions/%d/confirm" % a.id).status_code == 404
    assert Task.query.filter_by(title="Admin only").count() == 0


def test_confirm_is_post_only(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    assert c.get("/copilot/actions/1/confirm").status_code == 405


def test_planner_is_admin_only(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    assert c.get("/planner").status_code == 302
    assert c.post("/planner/generate").status_code == 302
    assert c.post("/planner/approve", data={"action_ids": ["1"]}).status_code == 302


def test_planner_generate_then_approve_selected_only(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.post("/planner/generate").get_data(as_text=True)
    assert "Restock Urea" in html and "Why" in html
    before = Task.query.count()
    assert before == 4                         # generating saved nothing
    ids = [str(a.id) for a in PendingAction.query.filter_by(source="planner", status="pending").all()
           if "Restock Urea" in a.preview]
    c.post("/planner/approve", data={"action_ids": ids})
    assert Task.query.count() == before + 1
    assert Task.query.filter_by(title="Restock Urea").count() == 1


def test_regenerating_supersedes_old_proposals(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    c.post("/planner/generate")
    first = PendingAction.query.filter_by(status="pending").count()
    c.post("/planner/generate")
    assert PendingAction.query.filter_by(status="pending").count() == first
    assert PendingAction.query.filter_by(status="superseded").count() == first


def test_weather_api_without_location(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    r = c.get("/api/weather").get_json()
    assert r["available"] is False and "FARM_LOCATION" in r["reason"]


def test_dashboards_render_for_both_roles(client_factory, data):
    for user, needle in ((data["admin"], "Recent farm activity"), (data["w1"], "My Assigned Tasks")):
        c = client_factory()
        login(c, user)
        r = c.get("/dashboard")
        assert r.status_code == 200 and needle in r.get_data(as_text=True)


def test_existing_pages_still_work(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    for path in ("/fields", "/crops", "/workers", "/tasks", "/inventory", "/expenses", "/reports"):
        assert c.get(path).status_code == 200, path


def test_worker_still_blocked_from_admin_pages(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    for path in ("/fields", "/workers", "/expenses", "/reports"):
        assert c.get(path).status_code == 302, path


def test_ai_added_task_shows_in_task_list_without_worker(client_factory, data):
    actions.confirm_action(actions.propose_action(
        data["admin_ctx"], "create_farm_task",
        {"title": "Unassigned AI task", "due_date": data["today"].isoformat()}).id, data["admin_ctx"])
    c = client_factory()
    login(c, data["admin"])
    assert "Unassigned AI task" in c.get("/tasks").get_data(as_text=True)


# ---------------- CSRF (enabled for these tests only)
def test_csrf_blocks_post_without_token(app, data):
    app.config["CSRF_ENABLED"] = True
    c = app.test_client()
    login(c, data["admin"])
    assert c.post("/copilot/chat", json={"message": "hi"}).status_code == 400
    assert c.post("/tasks/delete/1").status_code == 400
    assert c.post("/login", data={"email": "a@b.c", "password": "x"}).status_code == 400


def test_csrf_accepts_valid_header_and_form_token(app, data):
    app.config["CSRF_ENABLED"] = True
    c = app.test_client()
    login(c, data["admin"])
    c.get("/copilot")                                      # page render creates the token
    with c.session_transaction() as s:
        token = s["_csrf"]
    assert c.post("/copilot/chat", json={"message": "hi"}, headers={"X-CSRF-Token": token}).status_code == 200
    assert c.post("/copilot/clear", data={"csrf_token": token}).status_code == 302
    assert c.post("/copilot/chat", json={"message": "hi"}, headers={"X-CSRF-Token": "wrong"}).status_code == 400
