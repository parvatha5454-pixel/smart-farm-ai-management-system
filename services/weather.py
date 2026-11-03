"""Open-Meteo weather client. Returns real forecast data or an explicit 'unavailable' result."""
import time
from datetime import datetime, timezone

import requests

from services.ai.validation import validate_location

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 1800

_CACHE = {}


def clear_cache():
    _CACHE.clear()
    _DETAIL_CACHE.clear()


def _unavailable(reason):
    return {"available": False, "reason": reason, "source": "Open-Meteo"}


def _num(values, i):
    try:
        v = values[i]
    except (IndexError, TypeError):
        return None
    return v if isinstance(v, (int, float)) else None


def get_forecast(location, timeout=6, days=7):
    """Return a forecast dict. Raises ToolError only for an invalid location string."""
    loc = validate_location(location)
    key = loc.lower()
    cached = _CACHE.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    try:
        g = requests.get(GEOCODE_URL, params={"name": loc, "count": 1, "language": "en", "format": "json"},
                         timeout=timeout)
        g.raise_for_status()
        results = g.json().get("results") or []
        if not results:
            return _unavailable("Location '%s' was not found by the weather service." % loc)
        place = results[0]

        f = requests.get(FORECAST_URL, params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": days,
        }, timeout=timeout)
        f.raise_for_status()
        daily = f.json().get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            return _unavailable("The weather service returned no forecast days.")

        day_list = []
        for i, d in enumerate(dates):
            day_list.append({
                "date": d,
                "temp_max_c": _num(daily.get("temperature_2m_max"), i),
                "temp_min_c": _num(daily.get("temperature_2m_min"), i),
                "rain_mm": _num(daily.get("precipitation_sum"), i),
                "rain_chance_percent": _num(daily.get("precipitation_probability_max"), i),
            })
    except requests.Timeout:
        return _unavailable("The weather service timed out.")
    except requests.RequestException:
        return _unavailable("Could not reach the weather service.")
    except (ValueError, KeyError, TypeError):
        return _unavailable("The weather service returned unexpected data.")

    first3 = day_list[:3]
    rain_vals = [d["rain_mm"] for d in first3 if d["rain_mm"] is not None]
    temp_vals = [d["temp_max_c"] for d in first3 if d["temp_max_c"] is not None]
    name_parts = [place.get("name"), place.get("admin1"), place.get("country")]
    result = {
        "available": True,
        "source": "Open-Meteo (live forecast)",
        "location": ", ".join(p for p in name_parts if p),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "days": day_list,
        "summary": {
            "rain_next_3_days_mm": round(sum(rain_vals), 1) if rain_vals else None,
            "max_temp_next_3_days_c": round(max(temp_vals), 1) if temp_vals else None,
        },
    }
    _CACHE[key] = (time.monotonic(), result)
    return result


# ---------------------------------------------------------------------------
# Detailed forecast (current conditions, wind, humidity, derived alerts).
# Kept separate from get_forecast() so the original contract is unchanged.
# ---------------------------------------------------------------------------
_DETAIL_CACHE = {}

ALERT_HEAT_C = 38.0
ALERT_RAIN_MM = 25.0
ALERT_WIND_KMH = 40.0


def derive_alerts(days):
    """Threshold-based notices from forecast numbers. These are NOT official weather warnings."""
    alerts = []
    for d in days[:5]:
        if d.get("temp_max_c") is not None and d["temp_max_c"] >= ALERT_HEAT_C:
            alerts.append({"date": d["date"], "level": "warning", "title": "Very hot day",
                           "detail": "High of %.0f°C forecast." % d["temp_max_c"]})
        if d.get("rain_mm") is not None and d["rain_mm"] >= ALERT_RAIN_MM:
            alerts.append({"date": d["date"], "level": "warning", "title": "Heavy rain forecast",
                           "detail": "About %.0f mm of rain forecast." % d["rain_mm"]})
        if d.get("wind_max_kmh") is not None and d["wind_max_kmh"] >= ALERT_WIND_KMH:
            alerts.append({"date": d["date"], "level": "warning", "title": "Strong wind",
                           "detail": "Gusts of wind up to %.0f km/h forecast." % d["wind_max_kmh"]})
    return alerts


def irrigation_hints(days):
    """Planning hints from the forecast. Estimates only; never an irrigation instruction."""
    first3 = days[:3]
    rain = [d["rain_mm"] for d in first3 if d.get("rain_mm") is not None]
    highs = [d["temp_max_c"] for d in first3 if d.get("temp_max_c") is not None]
    total_rain = sum(rain) if rain else None
    hints = []
    if total_rain is None:
        return hints
    if total_rain >= 10:
        hints.append("About %.0f mm of rain is forecast over the next 3 days. You may be able to postpone "
                     "scheduled irrigation; check soil moisture by hand first." % total_rain)
    elif total_rain < 2 and highs and max(highs) >= 32:
        hints.append("Little rain (%.1f mm) and highs up to %.0f°C are forecast for the next 3 days. "
                     "Consider reviewing your irrigation schedule." % (total_rain, max(highs)))
    else:
        hints.append("No strong weather reason to change your irrigation plan in the next 3 days.")
    return hints


def get_detailed_forecast(location, timeout=6, days=7):
    """Return current conditions + daily forecast + derived alerts, or an explicit 'unavailable' result."""
    loc = validate_location(location)
    key = loc.lower()
    cached = _DETAIL_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    try:
        g = requests.get(GEOCODE_URL, params={"name": loc, "count": 1, "language": "en", "format": "json"},
                         timeout=timeout)
        g.raise_for_status()
        results = g.json().get("results") or []
        if not results:
            return _unavailable("Location '%s' was not found by the weather service." % loc)
        place = results[0]
        f = requests.get(FORECAST_URL, params={
            "latitude": place["latitude"], "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                     "precipitation_probability_max,wind_speed_10m_max",
            "timezone": "auto", "forecast_days": days,
        }, timeout=timeout)
        f.raise_for_status()
        body = f.json()
        daily = body.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            return _unavailable("The weather service returned no forecast days.")
        day_list = [{
            "date": d,
            "temp_max_c": _num(daily.get("temperature_2m_max"), i),
            "temp_min_c": _num(daily.get("temperature_2m_min"), i),
            "rain_mm": _num(daily.get("precipitation_sum"), i),
            "rain_chance_percent": _num(daily.get("precipitation_probability_max"), i),
            "wind_max_kmh": _num(daily.get("wind_speed_10m_max"), i),
        } for i, d in enumerate(dates)]
        cur = body.get("current") or {}
        current = {
            "temp_c": cur.get("temperature_2m") if isinstance(cur.get("temperature_2m"), (int, float)) else None,
            "humidity_percent": cur.get("relative_humidity_2m") if isinstance(cur.get("relative_humidity_2m"), (int, float)) else None,
            "wind_kmh": cur.get("wind_speed_10m") if isinstance(cur.get("wind_speed_10m"), (int, float)) else None,
            "rain_mm": cur.get("precipitation") if isinstance(cur.get("precipitation"), (int, float)) else None,
        }
    except requests.Timeout:
        return _unavailable("The weather service timed out.")
    except requests.RequestException:
        return _unavailable("Could not reach the weather service.")
    except (ValueError, KeyError, TypeError):
        return _unavailable("The weather service returned unexpected data.")

    name_parts = [place.get("name"), place.get("admin1"), place.get("country")]
    result = {
        "available": True, "source": "Open-Meteo (live forecast)",
        "location": ", ".join(p for p in name_parts if p),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current": current, "days": day_list,
        "alerts": derive_alerts(day_list), "irrigation_hints": irrigation_hints(day_list),
    }
    _DETAIL_CACHE[key] = (time.monotonic(), result)
    return result
