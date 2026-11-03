from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from models.inventory import InventoryItem
from routes.auth import login_required, admin_required

inventory_bp = Blueprint('inventory', __name__)

CATEGORIES = ['Seeds', 'Fertilizers', 'Pesticides', 'Tools', 'Equipment', 'Other']


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@inventory_bp.route('/inventory')
@login_required
def list_inventory():
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    query = InventoryItem.query
    if search:
        query = query.filter(InventoryItem.name.ilike(f'%{search}%'))
    if category_filter:
        query = query.filter(InventoryItem.category == category_filter)
    items = query.order_by(InventoryItem.created_at.desc()).all()
    return render_template('inventory/list.html', items=items, search=search,
                            category_filter=category_filter, categories=CATEGORIES,
                            is_admin=session.get('role') == 'admin')


@inventory_bp.route('/inventory/add', methods=['GET', 'POST'])
@admin_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '')
        quantity = request.form.get('quantity', '').strip()
        unit = request.form.get('unit', '').strip()
        min_stock = request.form.get('minimum_stock_level', '0').strip()
        purchase_date = parse_date(request.form.get('purchase_date', ''))
        supplier = request.form.get('supplier', '').strip()
        cost = request.form.get('cost', '0').strip()

        errors = []
        if not name:
            errors.append('Item name is required.')
        try:
            quantity_val = float(quantity)
            if quantity_val < 0:
                errors.append('Quantity cannot be negative.')
        except ValueError:
            errors.append('Quantity must be a valid number.')
            quantity_val = 0
        try:
            min_stock_val = float(min_stock) if min_stock else 0
            if min_stock_val < 0:
                errors.append('Minimum stock level cannot be negative.')
        except ValueError:
            errors.append('Minimum stock level must be a valid number.')
            min_stock_val = 0
        try:
            cost_val = float(cost) if cost else 0
            if cost_val < 0:
                errors.append('Cost cannot be negative.')
        except ValueError:
            errors.append('Cost must be a valid number.')
            cost_val = 0

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('inventory/form.html', item=dict(request.form),
                                    categories=CATEGORIES, mode='add')

        new_item = InventoryItem(name=name, category=category, quantity=quantity_val, unit=unit,
                                  minimum_stock_level=min_stock_val, purchase_date=purchase_date,
                                  supplier=supplier, cost=cost_val)
        db.session.add(new_item)
        db.session.commit()
        flash('Inventory item added successfully.', 'success')
        return redirect(url_for('inventory.list_inventory'))

    return render_template('inventory/form.html', item={}, categories=CATEGORIES, mode='add')


@inventory_bp.route('/inventory/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def edit_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '')
        quantity = request.form.get('quantity', '').strip()
        unit = request.form.get('unit', '').strip()
        min_stock = request.form.get('minimum_stock_level', '0').strip()
        purchase_date = parse_date(request.form.get('purchase_date', ''))
        supplier = request.form.get('supplier', '').strip()
        cost = request.form.get('cost', '0').strip()

        errors = []
        if not name:
            errors.append('Item name is required.')
        try:
            quantity_val = float(quantity)
            if quantity_val < 0:
                errors.append('Quantity cannot be negative.')
        except ValueError:
            errors.append('Quantity must be a valid number.')
            quantity_val = item.quantity
        try:
            min_stock_val = float(min_stock) if min_stock else 0
            if min_stock_val < 0:
                errors.append('Minimum stock level cannot be negative.')
        except ValueError:
            errors.append('Minimum stock level must be a valid number.')
            min_stock_val = item.minimum_stock_level
        try:
            cost_val = float(cost) if cost else 0
            if cost_val < 0:
                errors.append('Cost cannot be negative.')
        except ValueError:
            errors.append('Cost must be a valid number.')
            cost_val = item.cost

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('inventory/form.html', item=dict(request.form), item_id=item_id,
                                    categories=CATEGORIES, mode='edit')

        item.name = name
        item.category = category
        item.quantity = quantity_val
        item.unit = unit
        item.minimum_stock_level = min_stock_val
        item.purchase_date = purchase_date
        item.supplier = supplier
        item.cost = cost_val
        db.session.commit()
        flash('Inventory item updated successfully.', 'success')
        return redirect(url_for('inventory.list_inventory'))

    return render_template('inventory/form.html', item=item, item_id=item_id,
                            categories=CATEGORIES, mode='edit')


@inventory_bp.route('/inventory/delete/<int:item_id>', methods=['POST'])
@admin_required
def delete_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Inventory item deleted successfully.', 'success')
    return redirect(url_for('inventory.list_inventory'))
