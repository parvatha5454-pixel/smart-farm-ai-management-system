from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from models.field import Field
from routes.auth import admin_required

fields_bp = Blueprint('fields', __name__)

SOIL_TYPES = ['Alluvial', 'Black', 'Red', 'Laterite', 'Sandy', 'Clay', 'Loamy', 'Other']
IRRIGATION_TYPES = ['Drip', 'Sprinkler', 'Flood', 'Rain-fed', 'Canal', 'Other']


@fields_bp.route('/fields')
@admin_required
def list_fields():
    search = request.args.get('search', '').strip()
    query = Field.query
    if search:
        query = query.filter(Field.name.ilike(f'%{search}%'))
    all_fields = query.order_by(Field.created_at.desc()).all()
    return render_template('fields/list.html', fields=all_fields, search=search)


@fields_bp.route('/fields/add', methods=['GET', 'POST'])
@admin_required
def add_field():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        area = request.form.get('area', '').strip()
        soil_type = request.form.get('soil_type', '')
        irrigation_type = request.form.get('irrigation_type', '')

        errors = []
        if not name:
            errors.append('Field name is required.')
        try:
            area_val = float(area)
            if area_val <= 0:
                errors.append('Area must be a positive number.')
        except ValueError:
            errors.append('Area must be a valid number.')
            area_val = 0

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('fields/form.html', field=dict(request.form),
                                    soil_types=SOIL_TYPES, irrigation_types=IRRIGATION_TYPES, mode='add')

        new_field = Field(name=name, location=location, area=area_val,
                           soil_type=soil_type, irrigation_type=irrigation_type)
        db.session.add(new_field)
        db.session.commit()
        flash('Field added successfully.', 'success')
        return redirect(url_for('fields.list_fields'))

    return render_template('fields/form.html', field={}, soil_types=SOIL_TYPES,
                            irrigation_types=IRRIGATION_TYPES, mode='add')


@fields_bp.route('/fields/edit/<int:field_id>', methods=['GET', 'POST'])
@admin_required
def edit_field(field_id):
    field = Field.query.get_or_404(field_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        location = request.form.get('location', '').strip()
        area = request.form.get('area', '').strip()
        soil_type = request.form.get('soil_type', '')
        irrigation_type = request.form.get('irrigation_type', '')

        errors = []
        if not name:
            errors.append('Field name is required.')
        try:
            area_val = float(area)
            if area_val <= 0:
                errors.append('Area must be a positive number.')
        except ValueError:
            errors.append('Area must be a valid number.')
            area_val = field.area

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('fields/form.html', field=dict(request.form), field_id=field_id,
                                    soil_types=SOIL_TYPES, irrigation_types=IRRIGATION_TYPES, mode='edit')

        field.name = name
        field.location = location
        field.area = area_val
        field.soil_type = soil_type
        field.irrigation_type = irrigation_type
        db.session.commit()
        flash('Field updated successfully.', 'success')
        return redirect(url_for('fields.list_fields'))

    return render_template('fields/form.html', field=field, field_id=field_id,
                            soil_types=SOIL_TYPES, irrigation_types=IRRIGATION_TYPES, mode='edit')


@fields_bp.route('/fields/view/<int:field_id>')
@admin_required
def view_field(field_id):
    field = Field.query.get_or_404(field_id)
    return render_template('fields/view.html', field=field)


@fields_bp.route('/fields/delete/<int:field_id>', methods=['POST'])
@admin_required
def delete_field(field_id):
    field = Field.query.get_or_404(field_id)
    db.session.delete(field)
    db.session.commit()
    flash('Field deleted successfully.', 'success')
    return redirect(url_for('fields.list_fields'))
