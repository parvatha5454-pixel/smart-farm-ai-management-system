"""Read-only aggregations that power the dashboard, insights, analytics, calendar,
notifications and global search.

Everything here is computed from saved records. Anything derived from a forecast is labelled
basis='estimate'. Nothing is invented: when data is missing the result says so.
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func

from models import db
from models.crop import Crop
from models.expense import Expense
from models.farm_ops import CropObservation, IrrigationLog
from models.field import Field
from models.inventory import InventoryItem
from models.task import Task
from models.worker import Worker

HARVEST_SOON_DAYS = 7
HEALTH_RANK = {'Healthy': 0, 'Needs attention': 1, 'Stressed': 2}
OBS_HEALTH = ['Healthy', 'Needs attention', 'Stressed']
OBS_CATEGORIES = ['General', 'Pest', 'Disease', 'Nutrient', 'Water']
GROWTH_STAGES = ['Germination', 'Seedling', 'Vegetative', 'Flowering', 'Fruiting', 'Maturity', 'Harvest']
IRRIGATION_STATUSES = ['Planned', 'Done', 'Skipped']
IRRIGATION_METHODS = ['Drip', 'Sprinkler', 'Flood', 'Canal', 'Manual', 'Other']


def _is_open(t):
    return t.status != 'Completed'


# --------------------------------------------------------------------------- dashboard
def dashboard_extras(today=None):
    today = today or date.today()
    open_tasks = Task.query.filter(Task.status != 'Completed').all()
    upcoming = sorted([t for t in open_tasks if t.due_date and t.due_date >= today],
                      key=lambda t: t.due_date)[:6]
    due_today = len([t for t in open_tasks if t.due_date == today])
    total_tasks = Task.query.count()
    done = Task.query.filter_by(status='Completed').count()
    rate = round(100.0 * done / total_tasks) if total_tasks else None

    crop_rows = db.session.query(Crop.name, func.count(Crop.id)).filter(Crop.status != 'Harvested') \
        .group_by(Crop.name).order_by(func.count(Crop.id).desc()).limit(8).all()

    items = InventoryItem.query.all()
    low = [i for i in items if i.is_low_stock()]
    return {
        'upcoming_tasks': upcoming,
        'due_today': due_today,
        'task_completion_rate': rate,
        'crop_dist_labels': [r[0] for r in crop_rows],
        'crop_dist_values': [r[1] for r in crop_rows],
        'inventory_total': len(items),
        'inventory_low': len(low),
        'inventory_ok_percent': round(100.0 * (len(items) - len(low)) / len(items)) if items else None,
    }


# --------------------------------------------------------------------------- insights
def rule_insights(today=None, weather=None):
    """List of insight dicts. basis is 'recorded' (from saved data) or 'estimate' (forecast based)."""
    today = today or date.today()
    out = []

    def add(category, tone, title, detail, basis='recorded', link=None, link_label=None):
        out.append({'category': category, 'tone': tone, 'title': title, 'detail': detail,
                    'basis': basis, 'link': link, 'link_label': link_label})

    # Tasks
    open_tasks = Task.query.filter(Task.status != 'Completed').all()
    overdue = [t for t in open_tasks if t.due_date and t.due_date < today]
    if overdue:
        add('Task optimization', 'danger', '%d overdue task%s' % (len(overdue), '' if len(overdue) == 1 else 's'),
            'Oldest: "%s" (due %s). Finish, reschedule or cancel each one so the list stays trustworthy.'
            % (min(overdue, key=lambda t: t.due_date).title,
               min(overdue, key=lambda t: t.due_date).due_date.strftime('%d %b')),
            link='tasks.list_tasks', link_label='Open tasks')
    unassigned = [t for t in open_tasks if not t.worker_id]
    if unassigned:
        add('Task optimization', 'warning', '%d open task%s with no worker' % (len(unassigned), '' if len(unassigned) == 1 else 's'),
            'Assign a worker so someone owns each job.', link='tasks.list_tasks', link_label='Review tasks')
    loads = defaultdict(int)
    for t in open_tasks:
        if t.worker_id:
            loads[t.worker_id] += 1
    if len(loads) >= 2:
        hi, lo = max(loads.values()), min(loads.values())
        if hi - lo >= 3:
            names = {w.id: w.name for w in Worker.query.filter(Worker.id.in_(list(loads))).all()}
            busiest = max(loads, key=loads.get)
            add('Productivity', 'info', 'Uneven workload',
                '%s has %d open tasks while another worker has %d. Consider rebalancing.'
                % (names.get(busiest, 'One worker'), hi, lo), link='tasks.list_tasks', link_label='Rebalance')

    # Inventory
    for i in [i for i in InventoryItem.query.order_by(InventoryItem.name).all() if i.is_low_stock()][:4]:
        add('Inventory alert', 'warning', '%s is below minimum stock' % i.name,
            '%g %s on hand, minimum is %g.' % (i.quantity, i.unit or 'units', i.minimum_stock_level or 0),
            link='inventory.list_inventory', link_label='Open inventory')

    # Crops
    horizon = today + timedelta(days=HARVEST_SOON_DAYS)
    for c in Crop.query.all():
        if c.status == 'Harvested' or not c.expected_harvest_date:
            continue
        fname = c.field.name if c.field else 'unknown field'
        if c.expected_harvest_date < today:
            add('Crop observations', 'danger', '%s harvest date has passed' % c.name,
                'Expected %s in %s, status is "%s". Update the crop status or reschedule.'
                % (c.expected_harvest_date.strftime('%d %b'), fname, c.status),
                link='crops.view_crop', link_label='Open crop')
            out[-1]['link_args'] = {'crop_id': c.id}
        elif c.expected_harvest_date <= horizon:
            add('Crop observations', 'info', '%s is due for harvest soon' % c.name,
                'Expected %s in %s. Plan labour, equipment and storage.'
                % (c.expected_harvest_date.strftime('%d %b'), fname), link='crops.view_crop', link_label='Open crop')
            out[-1]['link_args'] = {'crop_id': c.id}

    # Crop health records
    for o in CropObservation.query.filter(CropObservation.health_status != 'Healthy') \
            .order_by(CropObservation.observed_on.desc()).limit(10).all():
        latest = CropObservation.query.filter_by(crop_id=o.crop_id).order_by(
            CropObservation.observed_on.desc(), CropObservation.id.desc()).first()
        if latest and latest.id == o.id:
            add('Crop observations', 'warning', '%s: %s' % (o.crop.name, o.health_status.lower()),
                'Latest observation (%s): %s' % (o.observed_on.strftime('%d %b'), o.notes or 'no notes added.'),
                link='smart.crop_health', link_label='Crop health')

    # Expenses
    month_start = today.replace(day=1)
    prev_end = month_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)

    def total(a, b):
        return db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
            Expense.date >= a, Expense.date <= b).scalar() or 0.0
    this_m, last_m = total(month_start, today), total(prev_start, prev_end)
    if last_m > 0 and this_m > last_m * 1.2:
        add('Expense insight', 'warning', 'Spending is ahead of last month',
            '₹%.0f so far this month versus ₹%.0f for all of last month.' % (this_m, last_m),
            link='expenses.list_expenses', link_label='Review expenses')
    top = db.session.query(Expense.category, func.sum(Expense.amount)).filter(
        Expense.date >= month_start, Expense.date <= today).group_by(Expense.category) \
        .order_by(func.sum(Expense.amount).desc()).first()
    if top and top[1]:
        add('Expense insight', 'info', 'Biggest cost this month: %s' % top[0], '₹%.0f recorded so far.' % top[1],
            link='expenses.list_expenses', link_label='Open expenses')

    # Irrigation log
    for f in Field.query.order_by(Field.name).all():
        has_crop = any(c.status in ('Planned', 'Growing', 'Ready for Harvest') for c in f.crops)
        if not has_crop:
            continue
        last = IrrigationLog.query.filter_by(field_id=f.id, status='Done') \
            .order_by(IrrigationLog.scheduled_for.desc()).first()
        if last is None:
            add('Productivity', 'info', 'No irrigation logged for %s' % f.name,
                'Log irrigation in the Irrigation page to build water-use history.',
                link='smart.irrigation', link_label='Open irrigation')
        elif (today - last.scheduled_for).days >= 7:
            add('Productivity', 'info', '%s: last irrigation logged %d days ago' % (f.name, (today - last.scheduled_for).days),
                'Only logged irrigations are counted. If you irrigated without logging it, add it.',
                link='smart.irrigation', link_label='Open irrigation')

    # Weather (estimate)
    if weather and weather.get('available'):
        from services.weather import irrigation_hints
        for h in irrigation_hints(weather.get('days') or []):
            add('Weather suggestion', 'info', 'Forecast-based irrigation note', h, basis='estimate',
                link='smart.weather', link_label='Weather details')
        for a in (weather.get('alerts') or [])[:2]:
            add('Weather suggestion', 'warning', '%s on %s' % (a['title'], a['date']), a['detail'], basis='estimate',
                link='smart.weather', link_label='Weather details')

    order = {'danger': 0, 'warning': 1, 'info': 2}
    out.sort(key=lambda x: order.get(x['tone'], 3))
    return out


# --------------------------------------------------------------------------- fields
def field_health(field):
    """Return (status, detail) using only recorded observations. Never guessed."""
    worst, latest_date = None, None
    for c in field.crops:
        if c.status == 'Harvested':
            continue
        o = CropObservation.query.filter_by(crop_id=c.id).order_by(
            CropObservation.observed_on.desc(), CropObservation.id.desc()).first()
        if not o:
            continue
        if worst is None or HEALTH_RANK.get(o.health_status, 0) > HEALTH_RANK.get(worst, 0):
            worst = o.health_status
        if latest_date is None or o.observed_on > latest_date:
            latest_date = o.observed_on
    if worst is None:
        return 'Not observed', 'No crop health observation recorded yet.'
    return worst, 'Latest observation on %s.' % latest_date.strftime('%d %b %Y')


def field_cards(today=None):
    today = today or date.today()
    cards = []
    for f in Field.query.order_by(Field.name).all():
        active = [c for c in f.crops if c.status != 'Harvested']
        health, health_detail = field_health(f)
        last_irr = IrrigationLog.query.filter_by(field_id=f.id, status='Done') \
            .order_by(IrrigationLog.scheduled_for.desc()).first()
        next_irr = IrrigationLog.query.filter(IrrigationLog.field_id == f.id, IrrigationLog.status == 'Planned',
                                              IrrigationLog.scheduled_for >= today) \
            .order_by(IrrigationLog.scheduled_for.asc()).first()
        history = []
        for c in f.crops:
            history.append((c.created_at.date() if c.created_at else c.planting_date, 'fa-seedling',
                            '%s planted %s' % (c.name, c.planting_date.strftime('%d %b %Y'))))
            for o in c.observations:
                history.append((o.observed_on, 'fa-magnifying-glass-plus',
                                '%s observed: %s' % (c.name, o.health_status.lower())))
        for l in f.irrigation_logs:
            history.append((l.scheduled_for, 'fa-droplet', 'Irrigation %s' % l.status.lower()))
        history.sort(key=lambda h: h[0], reverse=True)
        cards.append({
            'field': f, 'active_crops': active, 'health': health, 'health_detail': health_detail,
            'last_irrigation': last_irr, 'next_irrigation': next_irr, 'history': history[:5],
            'soil_recorded': bool(f.soil_type), 'irrigation_type': f.irrigation_type,
        })
    return cards


# --------------------------------------------------------------------------- crop health
def crop_health_rows():
    rows = []
    for c in Crop.query.order_by(Crop.name).all():
        obs = CropObservation.query.filter_by(crop_id=c.id).order_by(
            CropObservation.observed_on.desc(), CropObservation.id.desc()).all()
        rows.append({'crop': c, 'latest': obs[0] if obs else None, 'count': len(obs), 'history': obs[:5]})
    return rows


# --------------------------------------------------------------------------- analytics
def analytics(today=None):
    today = today or date.today()

    perf = db.session.query(Crop.name, func.sum(Crop.quantity)).group_by(Crop.name) \
        .order_by(func.sum(Crop.quantity).desc()).limit(10).all()

    prod = []
    for f in Field.query.order_by(Field.name).all():
        qty = sum((c.quantity or 0) for c in f.crops)
        if f.area and qty:
            prod.append((f.name, round(qty / f.area, 2)))

    worker_rows = []
    for w in Worker.query.order_by(Worker.name).all():
        done = len([t for t in w.tasks if t.status == 'Completed'])
        openn = len([t for t in w.tasks if t.status != 'Completed'])
        worker_rows.append((w.name, done, openn))

    # last 6 months of tasks created / completed (by due month) and expenses
    months = []
    y, m = today.year, today.month
    for _ in range(6):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    labels = ['%04d-%02d' % ym for ym in months]

    exp = {r[0]: r[1] for r in db.session.query(func.strftime('%Y-%m', Expense.date), func.sum(Expense.amount))
           .group_by(func.strftime('%Y-%m', Expense.date)).all()}
    created = {r[0]: r[1] for r in db.session.query(func.strftime('%Y-%m', Task.created_at), func.count(Task.id))
               .group_by(func.strftime('%Y-%m', Task.created_at)).all()}
    completed = {r[0]: r[1] for r in db.session.query(func.strftime('%Y-%m', Task.due_date), func.count(Task.id))
                 .filter(Task.status == 'Completed').group_by(func.strftime('%Y-%m', Task.due_date)).all()}
    irr = {r[0]: r[1] for r in db.session.query(func.strftime('%Y-%m', IrrigationLog.scheduled_for),
                                                func.count(IrrigationLog.id))
           .filter(IrrigationLog.status == 'Done').group_by(func.strftime('%Y-%m', IrrigationLog.scheduled_for)).all()}

    exp_cat = db.session.query(Expense.category, func.sum(Expense.amount)).group_by(Expense.category).all()
    inv = [(i.name, i.quantity or 0, i.minimum_stock_level or 0, i.unit or '') for i in
           InventoryItem.query.order_by(InventoryItem.name).limit(12).all()]

    total_tasks = Task.query.count()
    done = Task.query.filter_by(status='Completed').count()
    return {
        'crop_perf_labels': [r[0] for r in perf], 'crop_perf_values': [round(r[1] or 0, 2) for r in perf],
        'field_prod_labels': [p[0] for p in prod], 'field_prod_values': [p[1] for p in prod],
        'worker_labels': [w[0] for w in worker_rows], 'worker_done': [w[1] for w in worker_rows],
        'worker_open': [w[2] for w in worker_rows],
        'month_labels': labels,
        'month_expenses': [round(exp.get(l, 0) or 0, 2) for l in labels],
        'month_tasks_created': [created.get(l, 0) for l in labels],
        'month_tasks_completed': [completed.get(l, 0) for l in labels],
        'month_irrigations': [irr.get(l, 0) for l in labels],
        'exp_cat_labels': [r[0] for r in exp_cat], 'exp_cat_values': [round(r[1] or 0, 2) for r in exp_cat],
        'inv_labels': [i[0] for i in inv], 'inv_qty': [i[1] for i in inv], 'inv_min': [i[2] for i in inv],
        'task_completion_rate': round(100.0 * done / total_tasks) if total_tasks else None,
        'total_tasks': total_tasks, 'done_tasks': done,
    }


# --------------------------------------------------------------------------- irrigation
def irrigation_summary(today=None):
    today = today or date.today()
    logs = IrrigationLog.query.order_by(IrrigationLog.scheduled_for.desc(), IrrigationLog.id.desc()).limit(60).all()
    by_field = []
    for f in Field.query.order_by(Field.name).all():
        done = [l for l in f.irrigation_logs if l.status == 'Done']
        planned = sorted([l for l in f.irrigation_logs if l.status == 'Planned'], key=lambda l: l.scheduled_for)
        liters = sum(l.water_liters or 0 for l in done)
        by_field.append({
            'field': f, 'last': max(done, key=lambda l: l.scheduled_for) if done else None,
            'next': next((l for l in planned if l.scheduled_for >= today), None),
            'overdue_planned': [l for l in planned if l.scheduled_for < today],
            'liters': liters, 'sessions': len(done),
            'suggest': (max(done, key=lambda l: l.scheduled_for).scheduled_for + timedelta(days=3)) if done else None,
            'has_active_crop': any(c.status != 'Harvested' for c in f.crops),
        })
    # weekly water use for last 8 weeks (only logged liters)
    start = today - timedelta(weeks=8)
    weekly = defaultdict(float)
    for l in IrrigationLog.query.filter(IrrigationLog.status == 'Done', IrrigationLog.scheduled_for >= start).all():
        wk = l.scheduled_for - timedelta(days=l.scheduled_for.weekday())
        weekly[wk] += l.water_liters or 0
    weeks = [(today - timedelta(days=today.weekday())) - timedelta(weeks=i) for i in range(7, -1, -1)]
    return {'logs': logs, 'by_field': by_field,
            'week_labels': [w.strftime('%d %b') for w in weeks],
            'week_liters': [round(weekly.get(w, 0), 1) for w in weeks],
            'any_liters': any(weekly.values())}


# --------------------------------------------------------------------------- calendar
CAL_COLORS = {'task': '#167A50', 'harvest': '#B7791F', 'planting': '#4F7A3A', 'irrigation': '#0F766E',
              'overdue': '#B3261E'}


def calendar_events(role, user_id, today=None):
    today = today or date.today()
    events = []
    if role == 'admin':
        tasks = Task.query.filter(Task.due_date.isnot(None)).all()
    else:
        w = Worker.query.filter_by(user_id=user_id).first()
        tasks = Task.query.filter(Task.worker_id == w.id, Task.due_date.isnot(None)).all() if w else []
    for t in tasks:
        overdue = t.status != 'Completed' and t.due_date < today
        events.append({
            'date': t.due_date.isoformat(), 'type': 'overdue' if overdue else 'task',
            'title': t.title, 'detail': '%s priority · %s%s' % (t.priority, t.status,
                                                               (' · ' + t.worker.name) if t.worker else ''),
            'url': None, 'done': t.status == 'Completed'})
    for c in Crop.query.all():
        events.append({'date': c.planting_date.isoformat(), 'type': 'planting', 'title': 'Planting: %s' % c.name,
                       'detail': c.field.name if c.field else '', 'url': None, 'done': c.planting_date < today})
        if c.expected_harvest_date:
            events.append({'date': c.expected_harvest_date.isoformat(), 'type': 'harvest',
                           'title': 'Harvest: %s' % c.name, 'detail': 'Expected · %s' % (c.field.name if c.field else ''),
                           'url': None, 'done': c.status == 'Harvested'})
    for l in IrrigationLog.query.all():
        events.append({'date': l.scheduled_for.isoformat(), 'type': 'irrigation',
                       'title': 'Irrigation: %s' % (l.field.name if l.field else 'field'),
                       'detail': l.status, 'url': None, 'done': l.status == 'Done'})
    return events


# --------------------------------------------------------------------------- notifications / search
def notifications(role, user_id, today=None):
    today = today or date.today()
    items = []
    if role == 'admin':
        tasks = Task.query.filter(Task.status != 'Completed').all()
    else:
        w = Worker.query.filter_by(user_id=user_id).first()
        tasks = Task.query.filter(Task.worker_id == w.id, Task.status != 'Completed').all() if w else []
    overdue = [t for t in tasks if t.due_date and t.due_date < today]
    due_today = [t for t in tasks if t.due_date == today]
    if overdue:
        items.append({'tone': 'danger', 'icon': 'fa-circle-exclamation', 'text': '%d overdue task%s' % (len(overdue), '' if len(overdue) == 1 else 's'), 'endpoint': 'tasks.list_tasks'})
    if due_today:
        items.append({'tone': 'warning', 'icon': 'fa-clock', 'text': '%d task%s due today' % (len(due_today), '' if len(due_today) == 1 else 's'), 'endpoint': 'tasks.list_tasks'})
    low = [i for i in InventoryItem.query.all() if i.is_low_stock()]
    if low:
        items.append({'tone': 'warning', 'icon': 'fa-boxes-stacked', 'text': '%d item%s below minimum stock' % (len(low), '' if len(low) == 1 else 's'), 'endpoint': 'inventory.list_inventory'})
    soon = [c for c in Crop.query.all() if c.status != 'Harvested' and c.expected_harvest_date
            and today <= c.expected_harvest_date <= today + timedelta(days=HARVEST_SOON_DAYS)]
    if soon:
        items.append({'tone': 'info', 'icon': 'fa-wheat-awn', 'text': '%d crop%s due for harvest within a week' % (len(soon), '' if len(soon) == 1 else 's'), 'endpoint': 'crops.list_crops'})
    return items


def search(q, role, limit=5):
    q = (q or '').strip()
    if len(q) < 2:
        return []
    like = '%' + q.replace('%', '').replace('_', '') + '%'
    results = []
    if role == 'admin':
        for f in Field.query.filter(Field.name.ilike(like)).limit(limit).all():
            results.append({'group': 'Fields', 'title': f.name, 'sub': '%g acres' % f.area, 'endpoint': 'fields.view_field', 'args': {'field_id': f.id}, 'icon': 'fa-map'})
        for w in Worker.query.filter(Worker.name.ilike(like)).limit(limit).all():
            results.append({'group': 'Workers', 'title': w.name, 'sub': w.role or '', 'endpoint': 'workers.view_worker', 'args': {'worker_id': w.id}, 'icon': 'fa-people-group'})
    for c in Crop.query.filter(Crop.name.ilike(like)).limit(limit).all():
        results.append({'group': 'Crops', 'title': c.name, 'sub': c.status, 'endpoint': 'crops.view_crop', 'args': {'crop_id': c.id}, 'icon': 'fa-seedling'})
    if role == 'admin':
        for t in Task.query.filter(Task.title.ilike(like)).limit(limit).all():
            results.append({'group': 'Tasks', 'title': t.title, 'sub': t.status, 'endpoint': 'tasks.list_tasks', 'args': {'search': t.title}, 'icon': 'fa-list-check'})
    for i in InventoryItem.query.filter(InventoryItem.name.ilike(like)).limit(limit).all():
        results.append({'group': 'Inventory', 'title': i.name, 'sub': '%g %s' % (i.quantity, i.unit or ''), 'endpoint': 'inventory.list_inventory', 'args': {'search': i.name}, 'icon': 'fa-boxes-stacked'})
    return results
