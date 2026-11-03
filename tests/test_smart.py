from datetime import date, timedelta
from unittest import mock

from models import db
from models.crop import Crop
from models.farm_ops import CropObservation, IrrigationLog
from models.field import Field
from tests.helpers import login

ADMIN_PAGES = ["/dashboard", "/fields/overview", "/insights", "/weather", "/irrigation", "/crop-health",
               "/analytics", "/calendar", "/copilot", "/planner", "/reports", "/fields", "/crops", "/workers",
               "/tasks", "/inventory", "/expenses", "/profile", "/fields/add", "/crops/add", "/workers/add",
               "/tasks/add", "/inventory/add", "/expenses/add"]
WORKER_PAGES = ["/dashboard", "/weather", "/irrigation", "/crop-health", "/calendar", "/copilot", "/tasks",
                "/crops", "/inventory", "/profile"]


def test_every_page_renders_for_admin(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    for path in ADMIN_PAGES:
        r = c.get(path)
        assert r.status_code == 200, path
        assert "SmartFarm AI" in r.get_data(as_text=True)


def test_every_page_renders_for_worker(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    for path in WORKER_PAGES:
        assert c.get(path).status_code == 200, path


def test_public_pages_render(client_factory, data):
    c = client_factory()
    for path in ("/", "/login", "/register", "/does-not-exist"):
        r = c.get(path)
        assert r.status_code in (200, 404), path
    assert "does not exist" in c.get("/does-not-exist").get_data(as_text=True)


def test_new_pages_require_login(client_factory, data):
    c = client_factory()
    for path in ("/fields/overview", "/insights", "/weather", "/irrigation", "/crop-health", "/analytics",
                 "/calendar", "/api/calendar", "/api/search?q=to", "/api/notifications", "/api/weather/detail"):
        assert c.get(path).status_code == 302, path


def test_worker_blocked_from_admin_smart_pages(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    for path in ("/fields/overview", "/insights", "/analytics"):
        assert c.get(path).status_code == 302, path
    assert c.post("/insights/ai").status_code == 302
    assert c.post("/irrigation/add", data={"field_id": 1}).status_code == 302


def test_irrigation_add_status_delete(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    f = Field.query.filter_by(name="North").first()
    r = c.post("/irrigation/add", data={"field_id": f.id, "scheduled_for": date.today().isoformat(),
                                        "status": "Planned", "duration_minutes": "30", "water_liters": "500"})
    assert r.status_code == 302
    log = IrrigationLog.query.one()
    assert log.status == "Planned" and log.water_liters == 500
    c.post("/irrigation/%d/status" % log.id, data={"status": "Done"})
    assert db.session.get(IrrigationLog, log.id).status == "Done"
    html = c.get("/irrigation").get_data(as_text=True)
    assert "not a controller" in html or "logbook" in html
    c.post("/irrigation/%d/delete" % log.id)
    assert IrrigationLog.query.count() == 0


def test_irrigation_rejects_bad_input(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    c.post("/irrigation/add", data={"field_id": 9999, "scheduled_for": "nope", "status": "Weird"})
    c.post("/irrigation/add", data={"field_id": 1, "scheduled_for": "2026-01-01", "status": "Done",
                                    "duration_minutes": "-5"})
    c.post("/irrigation/add", data={"field_id": 1, "scheduled_for": "2026-01-01", "status": "Done",
                                    "water_liters": "abc"})
    assert IrrigationLog.query.count() == 0


def test_worker_can_add_observation_but_not_delete(client_factory, data):
    c = client_factory()
    login(c, data["w1"])
    crop = Crop.query.filter_by(name="Tomato").first()
    r = c.post("/crop-health/add", data={"crop_id": crop.id, "observed_on": date.today().isoformat(),
                                         "health_status": "Needs attention", "category": "Pest",
                                         "growth_stage": "Fruiting", "notes": "Leaf curl on edge rows"})
    assert r.status_code == 302
    obs = CropObservation.query.one()
    assert obs.health_status == "Needs attention"
    assert c.post("/crop-health/%d/delete" % obs.id).status_code == 302
    assert CropObservation.query.count() == 1          # worker delete was refused
    html = c.get("/crop-health").get_data(as_text=True)
    assert "not diagnoses" in html


def test_observation_validation(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    crop = Crop.query.first()
    future = (date.today() + timedelta(days=3)).isoformat()
    c.post("/crop-health/add", data={"crop_id": crop.id, "observed_on": future, "health_status": "Healthy"})
    c.post("/crop-health/add", data={"crop_id": crop.id, "observed_on": date.today().isoformat(), "health_status": "Fine"})
    c.post("/crop-health/add", data={"crop_id": 9999, "observed_on": date.today().isoformat(), "health_status": "Healthy"})
    assert CropObservation.query.count() == 0


def test_field_health_only_from_recorded_observations(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.get("/fields/overview").get_data(as_text=True)
    assert "Not observed" in html and "Illustrative" in html
    crop = Crop.query.filter_by(name="Tomato").first()
    db.session.add(CropObservation(crop_id=crop.id, observed_on=date.today(), health_status="Stressed"))
    db.session.commit()
    assert "Stressed" in c.get("/fields/overview").get_data(as_text=True)


def test_calendar_api_scopes_by_role(client_factory, data):
    admin, worker = client_factory(), client_factory()
    login(admin, data["admin"]); login(worker, data["w1"])
    a = admin.get("/api/calendar").get_json()["events"]
    w = worker.get("/api/calendar").get_json()["events"]
    titles_a = {e["title"] for e in a}; titles_w = {e["title"] for e in w}
    assert "Other worker task" in titles_a and "Other worker task" not in titles_w
    assert "Water tomatoes" in titles_w
    assert any(e["type"] == "harvest" for e in a) and any(e["type"] == "overdue" for e in a)


def test_search_and_notifications(client_factory, data):
    admin, worker = client_factory(), client_factory()
    login(admin, data["admin"]); login(worker, data["w1"])
    res = admin.get("/api/search?q=Tom").get_json()["results"]
    assert any(r["title"] == "Tomato" for r in res)
    assert admin.get("/api/search?q=x").get_json()["results"] == []
    wres = worker.get("/api/search?q=North").get_json()["results"]
    assert not any(r["group"] == "Fields" for r in wres)       # workers cannot search fields/workers
    texts = " ".join(i["text"] for i in admin.get("/api/notifications").get_json()["items"])
    assert "overdue" in texts and "below minimum stock" in texts


def test_insights_are_labelled_and_grounded(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.get("/insights").get_data(as_text=True)
    assert "Urea is below minimum stock" in html and "Recorded" in html
    assert "AI is not set up" in html                           # no key -> honest message, no fake AI text


def test_insights_ai_without_key_is_honest(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    r = c.post("/insights/ai").get_json()
    assert r["ok"] is False and r["error"] == "not_configured"


def test_weather_detail_without_location_and_with_mock(client_factory, data, app):
    c = client_factory()
    login(c, data["admin"])
    r = c.get("/api/weather/detail").get_json()
    assert r["available"] is False and "FARM_LOCATION" in r["reason"]
    from services import weather
    days = [{"date": "2026-11-02", "temp_max_c": 40.0, "temp_min_c": 25.0, "rain_mm": 30.0,
             "rain_chance_percent": 80, "wind_max_kmh": 45.0}]
    alerts = weather.derive_alerts(days)
    assert {a["title"] for a in alerts} == {"Very hot day", "Heavy rain forecast", "Strong wind"}
    assert weather.irrigation_hints(days)[0].startswith("About 30 mm")
    assert weather.irrigation_hints([{"rain_mm": None, "temp_max_c": 30}]) == []


def test_analytics_renders_with_data(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.get("/analytics").get_data(as_text=True)
    assert "Productivity analytics" in html and "not tracked" in html


def test_existing_endpoints_still_registered(app):
    names = {r.endpoint for r in app.url_map.iter_rules()}
    for ep in ("dashboard.index", "fields.list_fields", "crops.list_crops", "workers.list_workers", "tasks.list_tasks",
               "inventory.list_inventory", "expenses.list_expenses", "reports.index", "copilot.index", "copilot.chat",
               "copilot.planner", "copilot.confirm", "copilot.reject", "auth.login", "auth.register", "auth.profile"):
        assert ep in names, ep


def test_flash_messages_reach_the_page(client_factory, data):
    c = client_factory()
    r = c.post("/login", data={"email": "nobody@x.com", "password": "bad"})
    assert "Invalid email or password." in r.get_data(as_text=True)


def test_delete_still_works_with_confirm_form(client_factory, data):
    c = client_factory()
    login(c, data["admin"])
    html = c.get("/tasks").get_data(as_text=True)
    assert "confirm-delete-form" in html and 'data-item-name="Old task"' in html
