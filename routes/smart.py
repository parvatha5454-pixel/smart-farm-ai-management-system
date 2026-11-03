"""SmartFarm AI additions: field overview, insights, weather, irrigation, crop health,
analytics, calendar, plus small JSON helpers (search, notifications).

Roles: Admin sees everything. Workers can view irrigation/crop health/weather/calendar (their own
tasks only) and add crop health observations. Only admins change irrigation records or delete anything.
"""
from datetime import date, datetime

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template, request,
                   session, url_for)

from models import db
from models.crop import Crop
from models.farm_ops import CropObservation, IrrigationLog
from models.field import Field
from models.user import User
from routes.auth import admin_required, login_required
from services import insights
from services import weather as weather_service
from services.ai.agent import run_agent
from services.ai.llm import get_client
from services.ai.tools import UserCtx
from services.ai.validation import ToolError

smart_bp = Blueprint('smart', __name__)

INSIGHT_PROMPT = (
    "Give a short briefing on my farm using your tools. Use two parts: 'Facts (from my records)' and "
    "'Recommendations (suggestions, not facts)'. Cover overdue or open tasks, this month's expenses, low stock, "
    "crops nearing harvest, and the weather forecast if available. Do not create tasks.")


def _parse_date(value):
    try:
        return datetime.strptime(value or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _weather(detailed=True):
    loc = current_app.config.get('FARM_LOCATION', '')
    if not loc:
        return {'available': False, 'reason': 'No farm location set. Add FARM_LOCATION to your .env file.'}
    try:
        fn = weather_service.get_detailed_forecast if detailed else weather_service.get_forecast
        return fn(loc, timeout=current_app.config.get('WEATHER_TIMEOUT_SECONDS', 6))
    except ToolError as e:
        return {'available': False, 'reason': e.message}


def _ctx():
    user = db.session.get(User, session.get('user_id'))
    return UserCtx(id=user.id, role=user.role, name=user.full_name) if user else None


# ------------------------------------------------------------------ fields overview
@smart_bp.route('/fields/overview')
@admin_required
def field_overview():
    cards = insights.field_cards()
    total_area = sum(c['field'].area or 0 for c in cards)
    return render_template('smart/field_overview.html', cards=cards, total_area=total_area)


# ------------------------------------------------------------------ AI insights
@smart_bp.route('/insights')
@admin_required
def insights_center():
    weather = _weather()
    items = insights.rule_insights(weather=weather)
    return render_template('smart/insights.html', items=items, weather=weather,
                           ai_configured=get_client(current_app.config).is_configured(),
                           categories=sorted({i['category'] for i in items}))


@smart_bp.route('/insights/ai', methods=['POST'])
@admin_required
def insights_ai():
    ctx = _ctx()
    if ctx is None:
        return jsonify({'ok': False, 'error': 'Please log in again.'}), 401
    result = run_agent(ctx, INSIGHT_PROMPT, [])
    return jsonify(result)


# ------------------------------------------------------------------ weather
@smart_bp.route('/weather')
@login_required
def weather():
    return render_template('smart/weather.html', farm_location=current_app.config.get('FARM_LOCATION', ''))


@smart_bp.route('/api/weather/detail')
@login_required
def api_weather_detail():
    return jsonify(_weather())


# ------------------------------------------------------------------ irrigation
@smart_bp.route('/irrigation')
@login_required
def irrigation():
    summary = insights.irrigation_summary()
    return render_template('smart/irrigation.html', summary=summary, fields=Field.query.order_by(Field.name).all(),
                           statuses=insights.IRRIGATION_STATUSES, methods=insights.IRRIGATION_METHODS,
                           is_admin=session.get('role') == 'admin', today=date.today(),
                           weather=_weather() if session.get('role') == 'admin' else None)


@smart_bp.route('/irrigation/add', methods=['POST'])
@admin_required
def irrigation_add():
    field = db.session.get(Field, request.form.get('field_id', type=int) or 0)
    when = _parse_date(request.form.get('scheduled_for'))
    status = request.form.get('status', 'Planned')
    method = request.form.get('method', '')
    errors = []
    if field is None:
        errors.append('Choose a field.')
    if when is None:
        errors.append('Enter a valid date.')
    if status not in insights.IRRIGATION_STATUSES:
        errors.append('Choose a valid status.')
    minutes = water = None
    try:
        raw = request.form.get('duration_minutes', '').strip()
        minutes = int(raw) if raw else None
        raw = request.form.get('water_liters', '').strip()
        water = float(raw) if raw else None
        if (minutes is not None and minutes <= 0) or (water is not None and water < 0):
            errors.append('Duration must be above zero and water cannot be negative.')
    except ValueError:
        errors.append('Duration and water must be numbers.')
    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('smart.irrigation'))
    db.session.add(IrrigationLog(field_id=field.id, scheduled_for=when, duration_minutes=minutes,
                                 water_liters=water, method=method if method in insights.IRRIGATION_METHODS else None,
                                 status=status, notes=request.form.get('notes', '').strip()[:300],
                                 created_by=session.get('user_id')))
    db.session.commit()
    flash('Irrigation %s for %s saved.' % ('record' if status != 'Planned' else 'plan', field.name), 'success')
    return redirect(url_for('smart.irrigation'))


@smart_bp.route('/irrigation/<int:log_id>/status', methods=['POST'])
@admin_required
def irrigation_status(log_id):
    log = db.session.get(IrrigationLog, log_id)
    status = request.form.get('status', '')
    if log is None or status not in insights.IRRIGATION_STATUSES:
        flash('That irrigation record could not be updated.', 'danger')
    else:
        log.status = status
        db.session.commit()
        flash('Marked as %s.' % status.lower(), 'success')
    return redirect(url_for('smart.irrigation'))


@smart_bp.route('/irrigation/<int:log_id>/delete', methods=['POST'])
@admin_required
def irrigation_delete(log_id):
    log = db.session.get(IrrigationLog, log_id)
    if log:
        db.session.delete(log)
        db.session.commit()
        flash('Irrigation record deleted.', 'success')
    return redirect(url_for('smart.irrigation'))


# ------------------------------------------------------------------ crop health
@smart_bp.route('/crop-health')
@login_required
def crop_health():
    return render_template('smart/crop_health.html', rows=insights.crop_health_rows(),
                           crops=Crop.query.order_by(Crop.name).all(), health_options=insights.OBS_HEALTH,
                           categories=insights.OBS_CATEGORIES, stages=insights.GROWTH_STAGES,
                           is_admin=session.get('role') == 'admin', today=date.today())


@smart_bp.route('/crop-health/add', methods=['POST'])
@login_required
def crop_health_add():
    crop = db.session.get(Crop, request.form.get('crop_id', type=int) or 0)
    when = _parse_date(request.form.get('observed_on'))
    health = request.form.get('health_status', '')
    category = request.form.get('category', 'General')
    stage = request.form.get('growth_stage', '')
    errors = []
    if crop is None:
        errors.append('Choose a crop.')
    if when is None:
        errors.append('Enter a valid date.')
    elif when > date.today():
        errors.append('An observation cannot be dated in the future.')
    if health not in insights.OBS_HEALTH:
        errors.append('Choose a health status.')
    if errors:
        for e in errors:
            flash(e, 'danger')
        return redirect(url_for('smart.crop_health'))
    db.session.add(CropObservation(
        crop_id=crop.id, observed_on=when, health_status=health,
        growth_stage=stage if stage in insights.GROWTH_STAGES else None,
        category=category if category in insights.OBS_CATEGORIES else 'General',
        notes=request.form.get('notes', '').strip()[:500], created_by=session.get('user_id')))
    db.session.commit()
    flash('Observation saved for %s.' % crop.name, 'success')
    return redirect(url_for('smart.crop_health'))


@smart_bp.route('/crop-health/<int:obs_id>/delete', methods=['POST'])
@admin_required
def crop_health_delete(obs_id):
    obs = db.session.get(CropObservation, obs_id)
    if obs:
        db.session.delete(obs)
        db.session.commit()
        flash('Observation deleted.', 'success')
    return redirect(url_for('smart.crop_health'))


# ------------------------------------------------------------------ analytics
@smart_bp.route('/analytics')
@admin_required
def analytics_center():
    return render_template('smart/analytics.html', a=insights.analytics())


# ------------------------------------------------------------------ calendar
@smart_bp.route('/calendar')
@login_required
def calendar():
    return render_template('smart/calendar.html')


@smart_bp.route('/api/calendar')
@login_required
def api_calendar():
    return jsonify({'events': insights.calendar_events(session.get('role'), session.get('user_id'))})


# ------------------------------------------------------------------ helpers
@smart_bp.route('/api/search')
@login_required
def api_search():
    rows = insights.search(request.args.get('q', ''), session.get('role'))
    for r in rows:
        r['url'] = url_for(r.pop('endpoint'), **r.pop('args'))
    return jsonify({'results': rows})


@smart_bp.route('/api/notifications')
@login_required
def api_notifications():
    items = insights.notifications(session.get('role'), session.get('user_id'))
    for i in items:
        i['url'] = url_for(i.pop('endpoint'))
    return jsonify({'items': items})
