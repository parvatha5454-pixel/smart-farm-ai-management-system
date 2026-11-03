from flask import Blueprint, render_template
from sqlalchemy import func
from models import db
from models.field import Field
from models.crop import Crop
from models.worker import Worker
from models.task import Task
from models.inventory import InventoryItem
from models.expense import Expense
from routes.auth import admin_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@admin_required
def index():
    total_fields = Field.query.count()
    total_area = db.session.query(func.sum(Field.area)).scalar() or 0
    total_crops = Crop.query.count()
    total_workers = Worker.query.count()
    total_tasks = Task.query.count()
    total_expense_amount = db.session.query(func.sum(Expense.amount)).scalar() or 0
    total_inventory_value = db.session.query(func.sum(InventoryItem.cost)).scalar() or 0
    low_stock_items = [item for item in InventoryItem.query.all() if item.is_low_stock()]

    crop_by_status = db.session.query(Crop.status, func.count(Crop.id)).group_by(Crop.status).all()
    task_by_status = db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    expense_by_category = db.session.query(
        Expense.category, func.sum(Expense.amount)
    ).group_by(Expense.category).all()

    return render_template(
        'reports/index.html',
        total_fields=total_fields,
        total_area=total_area,
        total_crops=total_crops,
        total_workers=total_workers,
        total_tasks=total_tasks,
        total_expense_amount=total_expense_amount,
        total_inventory_value=total_inventory_value,
        low_stock_items=low_stock_items,
        crop_by_status=crop_by_status,
        task_by_status=task_by_status,
        expense_by_category=expense_by_category,
    )
