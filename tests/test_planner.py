from datetime import timedelta

from models import db
from models.task import Task
from services.planner import build_plan

HOT_DRY = {"available": True, "source": "Open-Meteo (live forecast)", "location": "Testville",
           "summary": {"rain_next_3_days_mm": 0.5, "max_temp_next_3_days_c": 36.0}}
WET = {"available": True, "source": "Open-Meteo (live forecast)", "location": "Testville",
       "summary": {"rain_next_3_days_mm": 25.0, "max_temp_next_3_days_c": 28.0}}
OFFLINE = {"available": False, "reason": "The weather service timed out."}


def titles(plan):
    return [s["title"] for s in plan["suggestions"]]


def test_recorded_data_suggestions_with_reasons(data):
    plan = build_plan(today=data["today"], weather=OFFLINE)
    t = titles(plan)
    assert "Review overdue tasks" in t
    assert "Prepare for harvest: Tomato (North)" in t
    assert "Restock Urea" in t
    assert all(s["reason"] for s in plan["suggestions"])
    assert plan["summary"]["overdue_tasks"] == 1


def test_no_weather_suggestions_when_forecast_unavailable(data):
    plan = build_plan(today=data["today"], weather=OFFLINE)
    assert not any("irrigation" in x or "rain" in x for x in titles(plan))
    assert any("Weather forecast unavailable" in m for m in plan["missing_information"])
    assert plan["weather"]["available"] is False


def test_hot_dry_forecast_suggests_irrigation_review_not_amounts(data):
    plan = build_plan(today=data["today"], weather=HOT_DRY)
    s = [x for x in plan["suggestions"] if x["title"] == "Review irrigation for North"][0]
    assert s["basis"] == "weather estimate" and "Forecast" in s["reason"]
    assert "litre" not in s["description"].lower() and "mm of water" not in s["description"].lower()
    assert plan["assumptions"]


def test_heavy_rain_suggestion(data):
    plan = build_plan(today=data["today"], weather=WET)
    assert "Review outdoor field work before expected rain" in titles(plan)
    assert "Review irrigation for North" not in titles(plan)


def test_missing_information_is_listed_not_invented(data):
    plan = build_plan(today=data["today"], weather=OFFLINE)
    text = " ".join(plan["missing_information"])
    assert "Chilli" in text            # no expected harvest date
    assert "South" in text             # no irrigation type
    assert "no minimum stock level" in text


def test_existing_open_task_is_not_suggested_again(data):
    db.session.add(Task(title="Restock Urea", status="Pending", due_date=data["today"]))
    db.session.commit()
    assert "Restock Urea" not in titles(build_plan(today=data["today"], weather=OFFLINE))


def test_suggested_dates_are_never_in_the_past(data):
    plan = build_plan(today=data["today"], weather=OFFLINE)
    assert all(s["due_date"] >= data["today"].isoformat() for s in plan["suggestions"])


def test_past_harvest_date_flagged(data):
    from models.crop import Crop
    c = Crop.query.filter_by(name="Chilli").one()
    c.expected_harvest_date = data["today"] - timedelta(days=2)
    db.session.commit()
    assert "Check harvest status: Chilli (North)" in titles(build_plan(today=data["today"], weather=OFFLINE))
