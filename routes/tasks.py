from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db
from models.task import Task
from models.worker import Worker
from routes.auth import login_required, admin_required

tasks_bp = Blueprint('tasks', __name__)

PRIORITIES = ['Low', 'Medium', 'High']
STATUSES = ['Pending', 'In Progress', 'Completed']


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@tasks_bp.route('/tasks')
@login_required
def list_tasks():
    is_admin = session.get('role') == 'admin'
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')

    if is_admin:
        query = Task.query
        if search:
            query = query.filter(Task.title.ilike(f'%{search}%'))
        if status_filter:
            query = query.filter(Task.status == status_filter)
        all_tasks = query.order_by(Task.due_date.asc()).all()
    else:
        worker = Worker.query.filter_by(user_id=session['user_id']).first()
        if worker:
            query = Task.query.filter_by(worker_id=worker.id)
            if status_filter:
                query = query.filter(Task.status == status_filter)
            all_tasks = query.order_by(Task.due_date.asc()).all()
        else:
            all_tasks = []

    return render_template('tasks/list.html', tasks=all_tasks, search=search,
                            status_filter=status_filter, statuses=STATUSES, is_admin=is_admin)


@tasks_bp.route('/tasks/add', methods=['GET', 'POST'])
@admin_required
def add_task():
    workers = Worker.query.all()
    if not workers:
        flash('Please add a worker before creating tasks.', 'warning')
        return redirect(url_for('workers.add_worker'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        worker_id = request.form.get('worker_id', '')
        due_date = parse_date(request.form.get('due_date', ''))
        priority = request.form.get('priority', 'Medium')
        status = request.form.get('status', 'Pending')

        errors = []
        if not title:
            errors.append('Task title is required.')
        if not worker_id:
            errors.append('Please assign a worker.')
        if not due_date:
            errors.append('A valid due date is required.')
        if priority not in PRIORITIES:
            errors.append('Invalid priority selected.')
        if status not in STATUSES:
            errors.append('Invalid status selected.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('tasks/form.html', task=dict(request.form), workers=workers,
                                    priorities=PRIORITIES, statuses=STATUSES, mode='add')

        worker = Worker.query.get(int(worker_id))
        new_task = Task(title=title, description=description, worker_id=int(worker_id),
                         assigned_to=worker.user_id if worker else None,
                         due_date=due_date, priority=priority, status=status)
        db.session.add(new_task)
        db.session.commit()
        flash('Task created and assigned successfully.', 'success')
        return redirect(url_for('tasks.list_tasks'))

    return render_template('tasks/form.html', task={}, workers=workers, priorities=PRIORITIES,
                            statuses=STATUSES, mode='add')


@tasks_bp.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@admin_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    workers = Worker.query.all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        worker_id = request.form.get('worker_id', '')
        due_date = parse_date(request.form.get('due_date', ''))
        priority = request.form.get('priority', 'Medium')
        status = request.form.get('status', 'Pending')

        errors = []
        if not title:
            errors.append('Task title is required.')
        if not worker_id:
            errors.append('Please assign a worker.')
        if not due_date:
            errors.append('A valid due date is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('tasks/form.html', task=dict(request.form), task_id=task_id,
                                    workers=workers, priorities=PRIORITIES, statuses=STATUSES, mode='edit')

        worker = Worker.query.get(int(worker_id))
        task.title = title
        task.description = description
        task.worker_id = int(worker_id)
        task.assigned_to = worker.user_id if worker else None
        task.due_date = due_date
        task.priority = priority
        task.status = status
        db.session.commit()
        flash('Task updated successfully.', 'success')
        return redirect(url_for('tasks.list_tasks'))

    return render_template('tasks/form.html', task=task, task_id=task_id, workers=workers,
                            priorities=PRIORITIES, statuses=STATUSES, mode='edit')


@tasks_bp.route('/tasks/update_status/<int:task_id>', methods=['POST'])
@login_required
def update_status(task_id):
    task = Task.query.get_or_404(task_id)

    # Workers can only update their own tasks
    if session.get('role') != 'admin':
        worker = Worker.query.filter_by(user_id=session['user_id']).first()
        if not worker or task.worker_id != worker.id:
            flash('You are not authorized to update this task.', 'danger')
            return redirect(url_for('tasks.list_tasks'))

    new_status = request.form.get('status', '')
    if new_status not in STATUSES:
        flash('Invalid status.', 'danger')
    else:
        task.status = new_status
        db.session.commit()
        flash('Task status updated.', 'success')

    return redirect(url_for('tasks.list_tasks'))


@tasks_bp.route('/tasks/delete/<int:task_id>', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully.', 'success')
    return redirect(url_for('tasks.list_tasks'))
