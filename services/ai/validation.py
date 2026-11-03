"""Pure input validation helpers (no Flask / database imports)."""
import re
from datetime import date, datetime, timedelta

PRIORITIES = ("Low", "Medium", "High")

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_LOCATION_RE = re.compile(r"^[\w\s,.'()\-]{2,100}$", re.UNICODE)


class ToolError(Exception):
    """A safe, user-presentable error raised by tools and validators."""

    def __init__(self, message, code="invalid_input"):
        super().__init__(message)
        self.message = message
        self.code = code


def reject_unknown(args, allowed):
    extra = sorted(str(k)[:40] for k in set(args) - set(allowed))
    if extra:
        raise ToolError("Unexpected parameter(s): " + ", ".join(extra))


def clean_text(value, field, max_len, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ToolError("%s must be text." % field)
    value = _CONTROL_CHARS.sub("", value).strip()
    if required and not value:
        raise ToolError("%s is required." % field)
    if len(value) > max_len:
        raise ToolError("%s must be at most %d characters." % (field, max_len))
    return value


def parse_iso_date(value, field, required=True):
    if value is None or value == "":
        if required:
            raise ToolError("%s is required (format YYYY-MM-DD)." % field)
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ToolError("%s must be a date in YYYY-MM-DD format." % field)
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ToolError("%s must be a valid date in YYYY-MM-DD format." % field)


def validate_date_range(start_raw, end_raw, today, max_days=366):
    start = parse_iso_date(start_raw, "start_date", required=False)
    end = parse_iso_date(end_raw, "end_date", required=False)
    if start is None:
        start = today.replace(day=1)
    if end is None:
        end = today
    if start > end:
        raise ToolError("start_date must not be after end_date.")
    if (end - start).days > max_days:
        raise ToolError("Date range is too long (maximum %d days)." % max_days)
    return start, end


def validate_task_args(args, today):
    reject_unknown(args, ("title", "description", "due_date", "priority"))
    title = clean_text(args.get("title"), "title", 150, required=True)
    description = clean_text(args.get("description"), "description", 1000)
    due = parse_iso_date(args.get("due_date"), "due_date", required=True)
    if due < today:
        raise ToolError("due_date cannot be in the past.")
    if due > today + timedelta(days=365):
        raise ToolError("due_date must be within the next 365 days.")
    priority = args.get("priority") or "Medium"
    if not isinstance(priority, str) or priority.strip().capitalize() not in PRIORITIES:
        raise ToolError("priority must be one of: Low, Medium, High.")
    return {
        "title": title,
        "description": description,
        "due_date": due.isoformat(),
        "priority": priority.strip().capitalize(),
    }


def validate_location(value):
    value = clean_text(value, "location", 100, required=True)
    if not _LOCATION_RE.match(value):
        raise ToolError("location contains invalid characters or is too short.")
    return value
