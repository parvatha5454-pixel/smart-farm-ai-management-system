"""Controlled tool registry. The AI can ONLY act through these functions.

Every call goes through prepare_call(): permission check -> input validation. Write tools
additionally require confirmed=True, which only the confirmation route sets after the user approves.
No tool accepts SQL, shell commands or code.
"""
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from flask import current_app
from sqlalchemy import func

from models import db
from models.crop import Crop
from models.expense import Expense
from models.field import Field
from models.inventory import InventoryItem
from models.task import Task
from models.worker import Worker
from services import weather as weather_service
from services.ai.validation import (ToolError, reject_unknown, validate_date_range,
                                    validate_location, validate_task_args)

ACTIVE_CROP_STATUSES = ("Planned", "Growing", "Ready for Harvest")
OPEN_TASK_STATUSES = ("Pending", "In Progress")


@dataclass(frozen=True)
class UserCtx:
    id: int
    role: str
    name: str = ""

    @property
    def is_admin(self):
        return self.role == "admin"


def _today():
    return date.today()


# ---------------------------------------------------------------- validators

def _no_args(args):
    reject_unknown(args, ())
    return {}


def _v_expense(args):
    reject_unknown(args, ("start_date", "end_date"))
    start, end = validate_date_range(args.get("start_date"), args.get("end_date"), _today())
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


def _v_task(args):
    return validate_task_args(args, _today())


def _v_weather(args):
    reject_unknown(args, ("location",))
    loc = args.get("location")
    if loc in (None, ""):
        loc = current_app.config.get("FARM_LOCATION", "")
        if not loc:
            return {"location": ""}
    return {"location": validate_location(loc)}


# ---------------------------------------------------------------- tool functions

def _task_row(t, today):
    return {
        "id": t.id,
        "title": t.title,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "priority": t.priority,
        "status": t.status,
        "assigned_worker": t.worker.name if t.worker else None,
        "overdue": bool(t.due_date and t.due_date < today and t.status != "Completed"),
    }


def get_farm_summary(ctx, args):
    today = _today()
    month_start = today.replace(day=1)
    month_total = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
        Expense.date >= month_start, Expense.date <= today).scalar() or 0.0
    return {
        "data_type": "recorded (from your database)",
        "as_of": today.isoformat(),
        "total_fields": Field.query.count(),
        "total_crops": Crop.query.count(),
        "active_crops": Crop.query.filter(Crop.status.in_(ACTIVE_CROP_STATUSES)).count(),
        "total_workers": Worker.query.count(),
        "open_tasks": Task.query.filter(Task.status.in_(OPEN_TASK_STATUSES)).count(),
        "overdue_tasks": Task.query.filter(Task.status != "Completed", Task.due_date < today).count(),
        "completed_tasks": Task.query.filter_by(status="Completed").count(),
        "low_stock_items": len([i for i in InventoryItem.query.all() if i.is_low_stock()]),
        "expenses_this_month": round(float(month_total), 2),
        "month": month_start.strftime("%B %Y"),
    }


def get_expense_summary(ctx, args):
    start = date.fromisoformat(args["start_date"])
    end = date.fromisoformat(args["end_date"])
    base = db.session.query(Expense).filter(Expense.date >= start, Expense.date <= end)
    total = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
        Expense.date >= start, Expense.date <= end).scalar() or 0.0
    rows = db.session.query(Expense.category, func.sum(Expense.amount), func.count(Expense.id)).filter(
        Expense.date >= start, Expense.date <= end).group_by(Expense.category).all()
    by_cat = sorted(
        ({"category": r[0], "total": round(float(r[1]), 2), "count": r[2]} for r in rows),
        key=lambda x: -x["total"])
    return {
        "data_type": "recorded (from your database)",
        "period": {"start_date": start.isoformat(), "end_date": end.isoformat()},
        "total_spent": round(float(total), 2),
        "number_of_expenses": base.count(),
        "by_category": by_cat,
        "currency": "INR",
    }


def get_pending_tasks(ctx, args):
    today = _today()
    q = Task.query.filter(Task.status.in_(OPEN_TASK_STATUSES))
    note = None
    if not ctx.is_admin:
        worker = Worker.query.filter_by(user_id=ctx.id).first()
        if not worker:
            return {"data_type": "recorded (from your database)", "open_tasks": 0, "overdue_tasks": 0,
                    "tasks": [], "note": "No worker profile is linked to your login, so no tasks are assigned."}
        q = q.filter(Task.worker_id == worker.id)
        note = "Showing only tasks assigned to you."
    tasks = q.order_by(Task.due_date.asc()).all()
    rows = [_task_row(t, today) for t in tasks]
    return {
        "data_type": "recorded (from your database)",
        "open_tasks": len(rows),
        "overdue_tasks": len([r for r in rows if r["overdue"]]),
        "tasks": rows[:50],
        "truncated": len(rows) > 50,
        "note": note,
        "meaning": "open = status Pending or In Progress",
    }


def get_inventory_alerts(ctx, args):
    items = [i for i in InventoryItem.query.order_by(InventoryItem.name).all() if i.is_low_stock()]
    no_min = InventoryItem.query.filter((InventoryItem.minimum_stock_level == None) |  # noqa: E711
                                        (InventoryItem.minimum_stock_level == 0)).count()
    return {
        "data_type": "recorded (from your database)",
        "low_stock_count": len(items),
        "items": [{
            "name": i.name, "category": i.category, "quantity": i.quantity, "unit": i.unit,
            "minimum_stock_level": i.minimum_stock_level,
            "shortfall": round(i.minimum_stock_level - i.quantity, 2),
        } for i in items],
        "items_without_minimum_level": no_min,
        "note": "An item is flagged when quantity is below its minimum stock level.",
    }


def get_field_and_crop_details(ctx, args):
    if ctx.is_admin:
        fields = Field.query.order_by(Field.name).all()
        return {
            "data_type": "recorded (from your database)",
            "fields": [{
                "name": f.name, "location": f.location, "area_acres": f.area, "soil_type": f.soil_type,
                "irrigation_type": f.irrigation_type,
                "crops": [{
                    "name": c.name, "status": c.status,
                    "planting_date": c.planting_date.isoformat() if c.planting_date else None,
                    "expected_harvest_date": c.expected_harvest_date.isoformat() if c.expected_harvest_date else None,
                    "quantity": c.quantity,
                } for c in f.crops],
            } for f in fields],
            "fields_without_crops": [f.name for f in fields if not f.crops],
        }
    crops = Crop.query.order_by(Crop.name).all()
    return {
        "data_type": "recorded (from your database)",
        "crops": [{"name": c.name, "status": c.status, "field": c.field.name if c.field else None,
                   "expected_harvest_date": c.expected_harvest_date.isoformat() if c.expected_harvest_date else None}
                  for c in crops],
        "note": "Field details are visible to farm owners only.",
    }


def create_farm_task(ctx, args):
    task = Task(title=args["title"], description=args["description"],
                due_date=date.fromisoformat(args["due_date"]), priority=args["priority"],
                status="Pending", worker_id=None, assigned_to=None)
    db.session.add(task)
    db.session.flush()
    return {"task_id": task.id, "title": task.title, "due_date": args["due_date"],
            "priority": task.priority, "status": "Pending", "assigned_worker": None}


def generate_weekly_farm_plan(ctx, args):
    from services.planner import build_plan
    return build_plan()


def get_weather_forecast(ctx, args):
    location = args.get("location", "")
    if not location:
        return {"available": False, "reason": "No location given and FARM_LOCATION is not set in the app settings."}
    return weather_service.get_forecast(
        location, timeout=current_app.config.get("WEATHER_TIMEOUT_SECONDS", 6))


# ---------------------------------------------------------------- registry

@dataclass(frozen=True)
class Tool:
    name: str
    label: str
    description: str
    parameters: dict
    validator: Callable
    func: Callable
    roles: tuple
    writes: bool = False
    preview: Optional[Callable] = None


def _task_preview(a):
    desc = (" Notes: " + a["description"]) if a["description"] else ""
    return "Create task \"%s\" (priority %s, due %s).%s" % (a["title"], a["priority"], a["due_date"], desc)


_EMPTY = {"type": "object", "properties": {}, "additionalProperties": False}
_BOTH = ("admin", "worker")

_TOOLS = [
    Tool("get_farm_summary", "Checking farm summary",
         "Get counts of fields, crops, workers, tasks, low-stock items and this month's expenses.",
         _EMPTY, _no_args, get_farm_summary, ("admin",)),
    Tool("get_expense_summary", "Checking expenses",
         "Get total and per-category recorded expenses between two dates. Dates are YYYY-MM-DD. "
         "If omitted, defaults to the current month so far.",
         {"type": "object", "properties": {
             "start_date": {"type": "string", "description": "YYYY-MM-DD"},
             "end_date": {"type": "string", "description": "YYYY-MM-DD"}},
          "additionalProperties": False},
         _v_expense, get_expense_summary, ("admin",)),
    Tool("get_pending_tasks", "Checking open tasks",
         "List open tasks (Pending or In Progress), including overdue ones. Workers see only their own.",
         _EMPTY, _no_args, get_pending_tasks, _BOTH),
    Tool("get_inventory_alerts", "Checking inventory stock",
         "List inventory items that are below their minimum stock level.",
         _EMPTY, _no_args, get_inventory_alerts, _BOTH),
    Tool("get_field_and_crop_details", "Checking fields and crops",
         "List fields with their crops, soil, irrigation type and harvest dates.",
         _EMPTY, _no_args, get_field_and_crop_details, _BOTH),
    Tool("create_farm_task", "Preparing a task proposal",
         "PROPOSE a new farm task. It is NOT saved until the user approves it.",
         {"type": "object", "properties": {
             "title": {"type": "string"},
             "description": {"type": "string"},
             "due_date": {"type": "string", "description": "YYYY-MM-DD, today or later"},
             "priority": {"type": "string", "enum": ["Low", "Medium", "High"]}},
          "required": ["title", "due_date"], "additionalProperties": False},
         _v_task, create_farm_task, ("admin",), writes=True, preview=_task_preview),
    Tool("generate_weekly_farm_plan", "Building weekly plan",
         "Build rule-based suggestions for the coming week from tasks, crops, inventory and weather. "
         "Returns suggestions with reasons and missing information. Does not save anything.",
         _EMPTY, _no_args, generate_weekly_farm_plan, ("admin",)),
    Tool("get_weather_forecast", "Checking weather forecast",
         "Get a real 7-day forecast from Open-Meteo. If location is omitted the farm's configured location is used.",
         {"type": "object", "properties": {"location": {"type": "string", "description": "City or town name"}},
          "additionalProperties": False},
         _v_weather, get_weather_forecast, _BOTH),
]

REGISTRY = {t.name: t for t in _TOOLS}


def openai_tool_specs(role):
    return [{"type": "function", "function": {"name": t.name, "description": t.description,
                                              "parameters": t.parameters}}
            for t in _TOOLS if role in t.roles]


def prepare_call(name, args, ctx):
    """Permission check + validation. Returns (tool, cleaned_args). Never executes anything."""
    tool = REGISTRY.get(name)
    if tool is None:
        raise ToolError("Unknown tool.", "unknown_tool")
    if ctx is None or ctx.role not in tool.roles:
        raise ToolError("You do not have permission to use this tool.", "forbidden")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolError("Tool arguments must be an object.")
    return tool, tool.validator(args)


def run_tool(name, args, ctx, confirmed=False):
    tool, cleaned = prepare_call(name, args, ctx)
    if tool.writes and not confirmed:
        raise ToolError("This action changes data and needs the user's confirmation first.",
                        "confirmation_required")
    return tool.func(ctx, cleaned)
