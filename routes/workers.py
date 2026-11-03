import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from models.worker import Worker
from routes.auth import admin_required

workers_bp = Blueprint('workers', __name__)
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@workers_bp.route('/workers')
@admin_required
def list_workers():
    search = request.args.get('search', '').strip()
    query = Worker.query
    if search:
        query = query.filter(Worker.name.ilike(f'%{search}%'))
    all_workers = query.order_by(Worker.created_at.desc()).all()
    return render_template('workers/list.html', workers=all_workers, search=search)


@workers_bp.route('/workers/add', methods=['GET', 'POST'])
@admin_required
def add_worker():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        role = request.form.get('role', '').strip()
        joining_date = parse_date(request.form.get('joining_date', ''))

        errors = []
        if not name:
            errors.append('Worker name is required.')
        if not phone:
            errors.append('Phone number is required.')
        if email and not EMAIL_REGEX.match(email):
            errors.append('Please enter a valid email address.')
        if not joining_date:
            errors.append('A valid joining date is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('workers/form.html', worker=dict(request.form), mode='add')

        new_worker = Worker(name=name, phone=phone, email=email, address=address,
                             role=role, joining_date=joining_date)
        db.session.add(new_worker)
        db.session.commit()
        flash('Worker added successfully.', 'success')
        return redirect(url_for('workers.list_workers'))

    return render_template('workers/form.html', worker={}, mode='add')


@workers_bp.route('/workers/edit/<int:worker_id>', methods=['GET', 'POST'])
@admin_required
def edit_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        role = request.form.get('role', '').strip()
        joining_date = parse_date(request.form.get('joining_date', ''))

        errors = []
        if not name:
            errors.append('Worker name is required.')
        if not phone:
            errors.append('Phone number is required.')
        if email and not EMAIL_REGEX.match(email):
            errors.append('Please enter a valid email address.')
        if not joining_date:
            errors.append('A valid joining date is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('workers/form.html', worker=dict(request.form), worker_id=worker_id, mode='edit')

        worker.name = name
        worker.phone = phone
        worker.email = email
        worker.address = address
        worker.role = role
        worker.joining_date = joining_date
        db.session.commit()
        flash('Worker updated successfully.', 'success')
        return redirect(url_for('workers.list_workers'))

    return render_template('workers/form.html', worker=worker, worker_id=worker_id, mode='edit')


@workers_bp.route('/workers/view/<int:worker_id>')
@admin_required
def view_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    return render_template('workers/view.html', worker=worker)


@workers_bp.route('/workers/delete/<int:worker_id>', methods=['POST'])
@admin_required
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    db.session.delete(worker)
    db.session.commit()
    flash('Worker deleted successfully.', 'success')
    return redirect(url_for('workers.list_workers'))
