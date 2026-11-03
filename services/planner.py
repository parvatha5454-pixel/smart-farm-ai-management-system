"""Rule-based weekly planner. Uses recorded data plus real forecast data when available.
No AI is needed. Every suggestion says WHY it was made; missing data is listed, not invented."""
from datetime import date, timedelta

from flask import current_app

from models.crop import Crop
from models.field import Field
from models.inventory import InventoryItem
from models.task import Task
from services import weather as weather_service
from services.ai.validation import ToolError

HARVEST_WINDOW_DAYS = 14
DRY_RAIN_MM = 2.0
HOT_TEMP_C = 32.0
HEAVY_RAIN_MM = 10.0

DISCLAIMER = ("These are planning prompts based on your records and the forecast. They are not expert advice. "
              "For irrigation amounts, fertilizer, pesticide or disease decisions, check with a local agriculture officer.")


def _fetch_weather():
    loc = current_app.config.get("FARM_LOCATION", "")
    if not loc:
        return {"available": False, "reason": "No farm location is configured (set FARM_LOCATION in .env)."}
    try:
        return weather_service.get_forecast(loc, timeout=current_app.config.get("WEATHER_TIMEOUT_SECONDS", 6))
    except ToolError as e:
        return {"available": False, "reason": e.message}


def build_plan(today=None, weather=None, fetch_weather=True):
    today = today or date.today()
    if weather is None:
        weather = _fetch_weather() if fetch_weather else {"available": False, "reason": "Weather not requested."}

    open_tasks = Task.query.filter(Task.status != "Completed").all()
    existing_titles = {(t.title or "").strip().lower() for t in open_tasks}
    overdue = [t for t in open_tasks if t.due_date and t.due_date < today]
    high_open = [t for t in open_tasks if t.priority == "High"]
    crops = Crop.query.all()
    fields = Field.query.order_by(Field.name).all()
    low_stock = [i for i in InventoryItem.query.order_by(InventoryItem.name).all() if i.is_low_stock()]

    suggestions, missing, assumptions = [], [], []
    seen = set()

    def suggest(title, description, due, priority, reason, basis):
        key = title.strip().lower()
        if key in existing_titles or key in seen:
            return
        seen.add(key)
        suggestions.append({"title": title, "description": description,
                            "due_date": max(due, today).isoformat(), "priority": priority,
                            "reason": reason, "basis": basis})

    # 1. Overdue tasks
    if overdue:
        suggest("Review overdue tasks",
                "%d task(s) are past their due date. Decide to finish, reschedule or cancel each one." % len(overdue),
                today, "High", "%d open task(s) have a due date before today (recorded)." % len(overdue), "recorded")

    # 2. Harvest timing
    harvest_horizon = today + timedelta(days=HARVEST_WINDOW_DAYS)
    for c in crops:
        if c.status == "Harvested" or not c.expected_harvest_date:
            continue
        fname = c.field.name if c.field else "unknown field"
        d = c.expected_harvest_date
        if d < today:
            suggest("Check harvest status: %s (%s)" % (c.name, fname),
                    "Expected harvest date has passed but the crop is not marked Harvested. Update its status or harvest plan.",
                    today, "High", "Expected harvest date was %s and status is '%s' (recorded)." % (d.isoformat(), c.status),
                    "recorded")
        elif d <= harvest_horizon:
            days_left = (d - today).days
            suggest("Prepare for harvest: %s (%s)" % (c.name, fname),
                    "Plan labour, equipment and storage before the expected harvest date.",
                    d - timedelta(days=3), "High" if days_left <= 7 else "Medium",
                    "Expected harvest date is %s, in %d day(s) (recorded)." % (d.isoformat(), days_left), "recorded")

    # 3. Low stock
    for i in low_stock:
        suggest("Restock %s" % i.name,
                "Current stock %s %s is below the minimum of %s." % (i.quantity, i.unit or "", i.minimum_stock_level),
                today + timedelta(days=3), "High" if (i.quantity or 0) <= 0 else "Medium",
                "Quantity %s is below the minimum stock level %s (recorded)." % (i.quantity, i.minimum_stock_level),
                "recorded")

    # 4. Weather-based prompts (only with real forecast data)
    weather_compact = {"available": False, "reason": weather.get("reason", "Unavailable")}
    if weather.get("available"):
        s = weather["summary"]
        weather_compact = {"available": True, "source": weather["source"], "location": weather["location"],
                           "rain_next_3_days_mm": s["rain_next_3_days_mm"],
                           "max_temp_next_3_days_c": s["max_temp_next_3_days_c"]}
        rain, hot = s["rain_next_3_days_mm"], s["max_temp_next_3_days_c"]
        assumptions.append("Weather rules: dry = under %.0f mm rain in 3 days; hot = highs of %.0f°C or more; "
                           "heavy rain = %.0f mm or more." % (DRY_RAIN_MM, HOT_TEMP_C, HEAVY_RAIN_MM))
        if rain is not None and hot is not None and rain < DRY_RAIN_MM and hot >= HOT_TEMP_C:
            for f in fields:
                growing = [c.name for c in f.crops if c.status == "Growing"]
                if growing and f.irrigation_type:
                    suggest("Review irrigation for %s" % f.name,
                            "Check soil moisture and decide if irrigation is needed. This is a prompt to check, "
                            "not an irrigation amount.",
                            today + timedelta(days=1), "Medium",
                            "Forecast: about %s mm rain and highs up to %s°C over 3 days. %s has growing crop(s) (%s) "
                            "using %s irrigation. (Forecast estimate)" % (rain, hot, f.name, ", ".join(growing),
                                                                         f.irrigation_type), "weather estimate")
        if rain is not None and rain >= HEAVY_RAIN_MM:
            suggest("Review outdoor field work before expected rain",
                    "Consider whether spraying, fertilizer application or harvesting should be moved. Check drainage.",
                    today, "Medium",
                    "Forecast shows about %s mm of rain over the next 3 days. (Forecast estimate)" % rain,
                    "weather estimate")
    else:
        missing.append("Weather forecast unavailable: %s" % weather.get("reason", "unknown reason"))

    # 5. Missing information
    no_harvest = sorted({c.name for c in crops if c.status != "Harvested" and not c.expected_harvest_date})
    if no_harvest:
        missing.append("No expected harvest date for: %s. Harvest reminders cannot be planned for these." %
                       ", ".join(no_harvest))
    no_irrig = [f.name for f in fields if not f.irrigation_type]
    if no_irrig:
        missing.append("No irrigation type recorded for: %s." % ", ".join(no_irrig))
    if not fields:
        missing.append("No fields are recorded yet.")
    if not crops:
        missing.append("No crops are recorded yet, so crop-based suggestions are limited.")
    no_min = InventoryItem.query.filter((InventoryItem.minimum_stock_level == None) |  # noqa: E711
                                        (InventoryItem.minimum_stock_level == 0)).count()
    if no_min:
        missing.append("%d inventory item(s) have no minimum stock level, so low-stock alerts cannot fire for them." % no_min)
    missing.append("Crop-specific schedules (sowing windows, fertilizer plans) are not stored in the app, so none were assumed.")

    return {
        "data_type": "rule-based suggestions (not saved)",
        "week_start": today.isoformat(),
        "week_end": (today + timedelta(days=6)).isoformat(),
        "summary": {"open_tasks": len(open_tasks), "overdue_tasks": len(overdue),
                    "high_priority_open_tasks": len(high_open), "low_stock_items": len(low_stock)},
        "overdue_task_titles": [t.title for t in overdue][:10],
        "weather": weather_compact,
        "suggestions": suggestions,
        "missing_information": missing,
        "assumptions": assumptions,
        "disclaimer": DISCLAIMER,
    }
