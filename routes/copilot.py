from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template,
                   request, session, url_for)

from models import db
from models.ai import ChatMessage, PendingAction
from models.user import User
from routes.auth import admin_required, login_required
from services import weather as weather_service
from services.ai import actions
from services.ai.agent import run_agent
from services.ai.llm import get_client
from services.ai.tools import REGISTRY, UserCtx, run_tool
from services.ai.validation import ToolError, clean_text
from services.planner import build_plan

copilot_bp = Blueprint('copilot', __name__)

EXAMPLES = {
    'admin': [
        'How much did I spend this month?',
        'Which inventory items are running low?',
        'Show me all pending farm tasks.',
        'Which field has which crop?',
        "Summarize this month's farm activities.",
        "Help me plan this week's farm tasks.",
        'Based on the weather forecast and my crops, should I review my irrigation schedule?',
    ],
    'worker': [
        'Show me my pending tasks.',
        'Which inventory items are running low?',
        'Which crops are growing on the farm?',
        'What is the weather forecast?',
    ],
}

QUICK_TOOLS = {
    'admin': [('get_farm_summary', 'Farm summary'), ('get_expense_summary', "This month's expenses"),
              ('get_pending_tasks', 'Open tasks'), ('get_inventory_alerts', 'Low stock'),
              ('get_field_and_crop_details', 'Fields and crops'), ('get_weather_forecast', 'Weather')],
    'worker': [('get_pending_tasks', 'My open tasks'), ('get_inventory_alerts', 'Low stock'),
               ('get_field_and_crop_details', 'Crops'), ('get_weather_forecast', 'Weather')],
}


def current_ctx():
    uid = session.get('user_id')
    if not uid:
        return None
    user = db.session.get(User, uid)
    if not user:
        return None
    return UserCtx(id=user.id, role=user.role, name=user.full_name)


def _json_error(message, status):
    return jsonify({'ok': False, 'error': message}), status


@copilot_bp.route('/copilot')
@login_required
def index():
    ctx = current_ctx()
    if ctx is None:
        session.clear()
        return redirect(url_for('auth.login'))
    history = ChatMessage.query.filter_by(user_id=ctx.id).order_by(ChatMessage.id.desc()).limit(30).all()[::-1]
    pending = PendingAction.query.filter_by(user_id=ctx.id, status='pending', source='copilot').all()
    return render_template(
        'copilot/index.html', history=history, examples=EXAMPLES.get(ctx.role, EXAMPLES['worker']),
        quick_tools=QUICK_TOOLS.get(ctx.role, QUICK_TOOLS['worker']),
        pending=[actions.serialize(a) for a in pending],
        ai_configured=get_client(current_app.config).is_configured())


@copilot_bp.route('/copilot/chat', methods=['POST'])
@login_required
def chat():
    ctx = current_ctx()
    if ctx is None:
        return _json_error('Please log in again.', 401)
    data = request.get_json(silent=True) or {}
    try:
        message = clean_text(data.get('message'), 'Message', 1000, required=True)
    except ToolError as e:
        return _json_error(e.message, 400)

    rows = ChatMessage.query.filter_by(user_id=ctx.id).order_by(ChatMessage.id.desc()).limit(10).all()[::-1]
    history = [{'role': r.role, 'content': r.content} for r in rows]
    result = run_agent(ctx, message, history)
    if result['ok']:
        db.session.add(ChatMessage(user_id=ctx.id, role='user', content=message))
        db.session.add(ChatMessage(user_id=ctx.id, role='assistant', content=result['reply']))
        db.session.commit()
    return jsonify(result)


@copilot_bp.route('/copilot/clear', methods=['POST'])
@login_required
def clear_history():
    ctx = current_ctx()
    if ctx:
        ChatMessage.query.filter_by(user_id=ctx.id).delete()
        db.session.commit()
    flash('Chat history cleared.', 'info')
    return redirect(url_for('copilot.index'))


@copilot_bp.route('/copilot/quick/<tool_name>', methods=['POST'])
@login_required
def quick_tool(tool_name):
    """Run a READ-ONLY tool directly (no AI needed)."""
    ctx = current_ctx()
    if ctx is None:
        return _json_error('Please log in again.', 401)
    tool = REGISTRY.get(tool_name)
    if tool is None or tool.writes:
        return _json_error('That tool is not available.', 404)
    args = (request.get_json(silent=True) or {}).get('args') or {}
    try:
        data = run_tool(tool_name, args, ctx)
        actions.log_audit(ctx, 'tool_call', tool_name, args)
        db.session.commit()
    except ToolError as e:
        return _json_error(e.message, 403 if e.code == 'forbidden' else 400)
    return jsonify({'ok': True, 'label': tool.label, 'data': data})


@copilot_bp.route('/copilot/actions/<int:action_id>/confirm', methods=['POST'])
@login_required
def confirm(action_id):
    ctx = current_ctx()
    if ctx is None:
        return _json_error('Please log in again.', 401)
    try:
        action = actions.confirm_action(action_id, ctx)
    except ToolError as e:
        code = {'forbidden': 403, 'not_found': 404, 'already_resolved': 409}.get(e.code, 400)
        return _json_error(e.message, code)
    return jsonify({'ok': True, 'action': action, 'message': 'Saved. The task was added to your Tasks list.'})


@copilot_bp.route('/copilot/actions/<int:action_id>/reject', methods=['POST'])
@login_required
def reject(action_id):
    ctx = current_ctx()
    if ctx is None:
        return _json_error('Please log in again.', 401)
    try:
        action = actions.reject_action(action_id, ctx)
    except ToolError as e:
        return _json_error(e.message, 404 if e.code == 'not_found' else 409)
    return jsonify({'ok': True, 'action': action, 'message': 'Proposal rejected. Nothing was saved.'})


@copilot_bp.route('/api/weather')
@login_required
def api_weather():
    loc = current_app.config.get('FARM_LOCATION', '')
    if not loc:
        return jsonify({'available': False, 'reason': 'No farm location set. Add FARM_LOCATION to your .env file.'})
    try:
        return jsonify(weather_service.get_forecast(
            loc, timeout=current_app.config.get('WEATHER_TIMEOUT_SECONDS', 6)))
    except ToolError as e:
        return jsonify({'available': False, 'reason': e.message})


# ------------------------------------------------------------------ Weekly planner

@copilot_bp.route('/planner')
@admin_required
def planner():
    ctx = current_ctx()
    pending = PendingAction.query.filter_by(user_id=ctx.id, status='pending', source='planner').all()
    return render_template('planner.html', plan=None, proposals=[actions.serialize(a) for a in pending])


@copilot_bp.route('/planner/generate', methods=['POST'])
@admin_required
def planner_generate():
    ctx = current_ctx()
    plan = build_plan()
    actions.supersede_planner_actions(ctx)
    proposals = []
    for s in plan['suggestions']:
        try:
            a = actions.propose_action(
                ctx, 'create_farm_task',
                {'title': s['title'], 'description': s['description'], 'due_date': s['due_date'],
                 'priority': s['priority']}, reason=s['reason'], source='planner')
            s['action_id'] = a.id
            proposals.append(actions.serialize(a))
        except ToolError as e:
            s['action_id'] = None
            s['error'] = e.message
    return render_template('planner.html', plan=plan, proposals=proposals)


@copilot_bp.route('/planner/approve', methods=['POST'])
@admin_required
def planner_approve():
    ctx = current_ctx()
    ids = request.form.getlist('action_ids')
    if not ids:
        flash('Select at least one suggestion to approve.', 'warning')
        return redirect(url_for('copilot.planner'))
    saved, failed = 0, 0
    for raw in ids:
        try:
            actions.confirm_action(int(raw), ctx)
            saved += 1
        except (ToolError, ValueError):
            failed += 1
    if saved:
        flash('%d task(s) saved to your Tasks list.' % saved, 'success')
    if failed:
        flash('%d suggestion(s) could not be saved (already handled or no longer valid).' % failed, 'warning')
    return redirect(url_for('tasks.list_tasks'))


@copilot_bp.route('/planner/discard', methods=['POST'])
@admin_required
def planner_discard():
    ctx = current_ctx()
    actions.supersede_planner_actions(ctx)
    flash('Unsaved suggestions discarded. Nothing was added to your tasks.', 'info')
    return redirect(url_for('copilot.planner'))
