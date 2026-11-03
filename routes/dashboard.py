from datetime import date
from flask import Blueprint, current_app, render_template, session
from sqlalchemy import func
from models import db
from models.field import Field
from models.crop import Crop
from models.worker import Worker
from models.task import Task
from models.inventory import InventoryItem
from models.expense import Expense
from routes.auth import login_required
from models.ai import PendingAction
from services.ai.llm import get_client
from services import insights

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    is_admin = session.get('role') == 'admin'

    if is_admin:
        total_fields = Field.query.count()
        total_crops = Crop.query.count()
        active_crops = Crop.query.filter(Crop.status.in_(['Planned', 'Growing', 'Ready for Harvest'])).count()
        total_workers = Worker.query.count()
        pending_tasks = Task.query.filter_by(status='Pending').count()
        completed_tasks = Task.query.filter_by(status='Completed').count()
        total_expenses = db.session.query(func.sum(Expense.amount)).scalar() or 0
        low_stock_items = [item for item in InventoryItem.query.all() if item.is_low_stock()]

        # Chart 1: Expense by category
        expense_by_cat = db.session.query(
            Expense.category, func.sum(Expense.amount)
        ).group_by(Expense.category).all()
        expense_labels = [row[0] for row in expense_by_cat]
        expense_values = [round(row[1], 2) for row in expense_by_cat]

        # Chart 2: Crop status
        crop_status_counts = db.session.query(
            Crop.status, func.count(Crop.id)
        ).group_by(Crop.status).all()
        crop_status_labels = [row[0] for row in crop_status_counts]
        crop_status_values = [row[1] for row in crop_status_counts]

        # Chart 3: Task status
        task_status_counts = db.session.query(
            Task.status, func.count(Task.id)
        ).group_by(Task.status).all()
        task_status_labels = [row[0] for row in task_status_counts]
        task_status_values = [row[1] for row in task_status_counts]

        # Chart 4: Monthly expenses (by month name, current data)
        monthly = db.session.query(
            func.strftime('%Y-%m', Expense.date), func.sum(Expense.amount)
        ).group_by(func.strftime('%Y-%m', Expense.date)).order_by(func.strftime('%Y-%m', Expense.date)).all()
        monthly_labels = [row[0] for row in monthly]
        monthly_values = [round(row[1], 2) for row in monthly]

        # --- SmartFarm AI additions (all values below are recorded data) ---
        today = date.today()
        month_start = today.replace(day=1)
        month_expense = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
            Expense.date >= month_start, Expense.date <= today).scalar() or 0.0
        overdue_tasks = Task.query.filter(Task.status != 'Completed', Task.due_date < today) \
            .order_by(Task.due_date.asc()).all()
        activities = []
        for t in Task.query.order_by(Task.created_at.desc()).limit(5).all():
            activities.append((t.created_at, 'fa-list-check', 'Task created: ' + t.title))
        for e in Expense.query.order_by(Expense.created_at.desc()).limit(5).all():
            activities.append((e.created_at, 'fa-money-bill-wave',
                               'Expense recorded: %s ₹%.2f' % (e.category, e.amount)))
        for c in Crop.query.order_by(Crop.created_at.desc()).limit(5).all():
            activities.append((c.created_at, 'fa-seedling', 'Crop added: ' + c.name))
        activities = sorted([a for a in activities if a[0]], key=lambda a: a[0], reverse=True)[:8]
        unsaved_suggestions = PendingAction.query.filter_by(
            user_id=session['user_id'], status='pending', source='planner').count()

        extras = insights.dashboard_extras(today)
        return render_template(
            'dashboard.html',
            is_admin=True,
            today=today,
            dash_insights=insights.rule_insights(today)[:4],
            **extras,
            month_label=month_start.strftime('%B %Y'),
            month_expense=month_expense,
            overdue_tasks=overdue_tasks,
            recent_activities=activities,
            unsaved_suggestions=unsaved_suggestions,
            ai_configured=get_client(current_app.config).is_configured(),
            farm_location=current_app.config.get('FARM_LOCATION', ''),
            total_fields=total_fields,
            total_crops=total_crops,
            active_crops=active_crops,
            total_workers=total_workers,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            total_expenses=total_expenses,
            low_stock_count=len(low_stock_items),
            low_stock_items=low_stock_items,
            expense_labels=expense_labels,
            expense_values=expense_values,
            crop_status_labels=crop_status_labels,
            crop_status_values=crop_status_values,
            task_status_labels=task_status_labels,
            task_status_values=task_status_values,
            monthly_labels=monthly_labels,
            monthly_values=monthly_values,
        )
    else:
        # Worker dashboard: only their own tasks
        worker = Worker.query.filter_by(user_id=session['user_id']).first()
        my_tasks = Task.query.filter_by(worker_id=worker.id).all() if worker else []
        pending = len([t for t in my_tasks if t.status == 'Pending'])
        in_progress = len([t for t in my_tasks if t.status == 'In Progress'])
        completed = len([t for t in my_tasks if t.status == 'Completed'])
        total_crops = Crop.query.count()

        return render_template(
            'dashboard.html',
            is_admin=False,
            my_tasks=my_tasks,
            pending=pending,
            in_progress=in_progress,
            completed=completed,
            total_crops=total_crops,
            worker=worker,
            today=date.today(),
            overdue_count=len([t for t in my_tasks if t.status != 'Completed' and t.due_date and t.due_date < date.today()]),
        )
