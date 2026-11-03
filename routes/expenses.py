from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from models.expense import Expense
from routes.auth import admin_required

expenses_bp = Blueprint('expenses', __name__)

CATEGORIES = ['Seeds', 'Fertilizer', 'Labour', 'Equipment', 'Irrigation', 'Transportation', 'Other']
PAYMENT_METHODS = ['Cash', 'Card', 'UPI', 'Bank Transfer', 'Other']


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@expenses_bp.route('/expenses')
@admin_required
def list_expenses():
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    query = Expense.query
    if search:
        query = query.filter(Expense.description.ilike(f'%{search}%'))
    if category_filter:
        query = query.filter(Expense.category == category_filter)
    expenses = query.order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template('expenses/list.html', expenses=expenses, search=search,
                            category_filter=category_filter, categories=CATEGORIES, total=total)


@expenses_bp.route('/expenses/add', methods=['GET', 'POST'])
@admin_required
def add_expense():
    if request.method == 'POST':
        category = request.form.get('category', '')
        amount = request.form.get('amount', '').strip()
        date_val = parse_date(request.form.get('date', ''))
        description = request.form.get('description', '').strip()
        payment_method = request.form.get('payment_method', '')

        errors = []
        if category not in CATEGORIES:
            errors.append('Please select a valid expense category.')
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                errors.append('Amount must be a positive number.')
        except ValueError:
            errors.append('Amount must be a valid number.')
            amount_val = 0
        if not date_val:
            errors.append('A valid date is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('expenses/form.html', expense=dict(request.form), categories=CATEGORIES,
                                    payment_methods=PAYMENT_METHODS, mode='add')

        new_expense = Expense(category=category, amount=amount_val, date=date_val,
                               description=description, payment_method=payment_method,
                               created_by=session.get('user_id'))
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense recorded successfully.', 'success')
        return redirect(url_for('expenses.list_expenses'))

    return render_template('expenses/form.html', expense={}, categories=CATEGORIES,
                            payment_methods=PAYMENT_METHODS, mode='add')


@expenses_bp.route('/expenses/edit/<int:expense_id>', methods=['GET', 'POST'])
@admin_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)

    if request.method == 'POST':
        category = request.form.get('category', '')
        amount = request.form.get('amount', '').strip()
        date_val = parse_date(request.form.get('date', ''))
        description = request.form.get('description', '').strip()
        payment_method = request.form.get('payment_method', '')

        errors = []
        if category not in CATEGORIES:
            errors.append('Please select a valid expense category.')
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                errors.append('Amount must be a positive number.')
        except ValueError:
            errors.append('Amount must be a valid number.')
            amount_val = expense.amount
        if not date_val:
            errors.append('A valid date is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('expenses/form.html', expense=dict(request.form), expense_id=expense_id,
                                    categories=CATEGORIES, payment_methods=PAYMENT_METHODS, mode='edit')

        expense.category = category
        expense.amount = amount_val
        expense.date = date_val
        expense.description = description
        expense.payment_method = payment_method
        db.session.commit()
        flash('Expense updated successfully.', 'success')
        return redirect(url_for('expenses.list_expenses'))

    return render_template('expenses/form.html', expense=expense, expense_id=expense_id,
                            categories=CATEGORIES, payment_methods=PAYMENT_METHODS, mode='edit')


@expenses_bp.route('/expenses/delete/<int:expense_id>', methods=['POST'])
@admin_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully.', 'success')
    return redirect(url_for('expenses.list_expenses'))
