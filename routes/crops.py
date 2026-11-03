from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from models.crop import Crop
from models.field import Field
from routes.auth import login_required, admin_required

crops_bp = Blueprint('crops', __name__)

CROP_STATUSES = ['Planned', 'Growing', 'Ready for Harvest', 'Harvested']


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@crops_bp.route('/crops')
@login_required
def list_crops():
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    query = Crop.query
    if search:
        query = query.filter(Crop.name.ilike(f'%{search}%'))
    if status_filter:
        query = query.filter(Crop.status == status_filter)
    all_crops = query.order_by(Crop.created_at.desc()).all()
    return render_template('crops/list.html', crops=all_crops, search=search,
                            status_filter=status_filter, statuses=CROP_STATUSES,
                            is_admin=session.get('role') == 'admin')


@crops_bp.route('/crops/add', methods=['GET', 'POST'])
@admin_required
def add_crop():
    fields = Field.query.all()
    if not fields:
        flash('Please add a field before adding crops.', 'warning')
        return redirect(url_for('fields.add_field'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        field_id = request.form.get('field_id', '')
        planting_date = parse_date(request.form.get('planting_date', ''))
        harvest_date = parse_date(request.form.get('expected_harvest_date', ''))
        status = request.form.get('status', 'Planned')
        quantity = request.form.get('quantity', '0').strip()
        notes = request.form.get('notes', '').strip()

        errors = []
        if not name:
            errors.append('Crop name is required.')
        if not field_id:
            errors.append('Please select a field.')
        if not planting_date:
            errors.append('A valid planting date is required.')
        if status not in CROP_STATUSES:
            errors.append('Invalid crop status.')
        try:
            quantity_val = float(quantity) if quantity else 0
            if quantity_val < 0:
                errors.append('Quantity cannot be negative.')
        except ValueError:
            errors.append('Quantity must be a valid number.')
            quantity_val = 0

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('crops/form.html', crop=dict(request.form), fields=fields,
                                    statuses=CROP_STATUSES, mode='add')

        new_crop = Crop(name=name, field_id=int(field_id), planting_date=planting_date,
                         expected_harvest_date=harvest_date, status=status,
                         quantity=quantity_val, notes=notes)
        db.session.add(new_crop)
        db.session.commit()
        flash('Crop added successfully.', 'success')
        return redirect(url_for('crops.list_crops'))

    return render_template('crops/form.html', crop={}, fields=fields, statuses=CROP_STATUSES, mode='add')


@crops_bp.route('/crops/edit/<int:crop_id>', methods=['GET', 'POST'])
@admin_required
def edit_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    fields = Field.query.all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        field_id = request.form.get('field_id', '')
        planting_date = parse_date(request.form.get('planting_date', ''))
        harvest_date = parse_date(request.form.get('expected_harvest_date', ''))
        status = request.form.get('status', 'Planned')
        quantity = request.form.get('quantity', '0').strip()
        notes = request.form.get('notes', '').strip()

        errors = []
        if not name:
            errors.append('Crop name is required.')
        if not field_id:
            errors.append('Please select a field.')
        if not planting_date:
            errors.append('A valid planting date is required.')
        try:
            quantity_val = float(quantity) if quantity else 0
            if quantity_val < 0:
                errors.append('Quantity cannot be negative.')
        except ValueError:
            errors.append('Quantity must be a valid number.')
            quantity_val = crop.quantity

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('crops/form.html', crop=dict(request.form), crop_id=crop_id,
                                    fields=fields, statuses=CROP_STATUSES, mode='edit')

        crop.name = name
        crop.field_id = int(field_id)
        crop.planting_date = planting_date
        crop.expected_harvest_date = harvest_date
        crop.status = status
        crop.quantity = quantity_val
        crop.notes = notes
        db.session.commit()
        flash('Crop updated successfully.', 'success')
        return redirect(url_for('crops.list_crops'))

    return render_template('crops/form.html', crop=crop, crop_id=crop_id, fields=fields,
                            statuses=CROP_STATUSES, mode='edit')


@crops_bp.route('/crops/view/<int:crop_id>')
@login_required
def view_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    return render_template('crops/view.html', crop=crop)


@crops_bp.route('/crops/delete/<int:crop_id>', methods=['POST'])
@admin_required
def delete_crop(crop_id):
    crop = Crop.query.get_or_404(crop_id)
    db.session.delete(crop)
    db.session.commit()
    flash('Crop deleted successfully.', 'success')
    return redirect(url_for('crops.list_crops'))
