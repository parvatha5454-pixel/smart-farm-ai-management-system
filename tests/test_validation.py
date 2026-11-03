import unittest
from datetime import date

from services.ai.validation import (ToolError, parse_iso_date, validate_date_range,
                                    validate_location, validate_task_args)

TODAY = date(2026, 10, 17)


class DateRangeTests(unittest.TestCase):
    def test_defaults_to_current_month_so_far(self):
        s, e = validate_date_range(None, None, TODAY)
        self.assertEqual((s, e), (date(2026, 10, 1), TODAY))

    def test_explicit_range(self):
        s, e = validate_date_range("2026-01-01", "2026-01-31", TODAY)
        self.assertEqual((s, e), (date(2026, 1, 1), date(2026, 1, 31)))

    def test_start_after_end_rejected(self):
        with self.assertRaises(ToolError):
            validate_date_range("2026-02-01", "2026-01-01", TODAY)

    def test_bad_format_rejected(self):
        for bad in ("01/02/2026", "2026-13-01", "yesterday", 12345):
            with self.assertRaises(ToolError):
                parse_iso_date(bad, "start_date")

    def test_range_too_long_rejected(self):
        with self.assertRaises(ToolError):
            validate_date_range("2020-01-01", "2026-01-01", TODAY)


class TaskArgsTests(unittest.TestCase):
    def ok(self, **kw):
        base = {"title": "Check pump", "due_date": "2026-10-20"}
        base.update(kw)
        return validate_task_args(base, TODAY)

    def test_valid_task_gets_defaults(self):
        r = self.ok()
        self.assertEqual(r["priority"], "Medium")
        self.assertEqual(r["description"], "")

    def test_priority_is_normalized(self):
        self.assertEqual(self.ok(priority="high")["priority"], "High")

    def test_invalid_priority(self):
        with self.assertRaises(ToolError):
            self.ok(priority="urgent")

    def test_missing_title(self):
        with self.assertRaises(ToolError):
            self.ok(title="   ")

    def test_title_too_long(self):
        with self.assertRaises(ToolError):
            self.ok(title="x" * 151)

    def test_past_due_date(self):
        with self.assertRaises(ToolError):
            self.ok(due_date="2026-10-16")

    def test_due_date_too_far(self):
        with self.assertRaises(ToolError):
            self.ok(due_date="2028-01-01")

    def test_unexpected_parameter_rejected(self):
        with self.assertRaises(ToolError):
            self.ok(sql="DROP TABLE tasks")

    def test_control_characters_removed(self):
        self.assertEqual(self.ok(title="Water\x00 field")["title"], "Water field")

    def test_non_text_title(self):
        with self.assertRaises(ToolError):
            self.ok(title=["a"])


class LocationTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_location(" Madurai, India "), "Madurai, India")

    def test_invalid(self):
        for bad in ("", "a", "x" * 101, "Paris; DROP TABLE", "<script>", None):
            with self.assertRaises(ToolError):
                validate_location(bad)


if __name__ == "__main__":
    unittest.main()
