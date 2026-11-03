import logging
import os
from flask import Flask, jsonify, render_template, request
from config import Config
from models import db
from services.security import init_csrf


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Secrets must come from the environment in production.
    if not app.config.get('SECRET_KEY'):
        if app.config.get('APP_ENV') == 'production' and not app.config.get('TESTING'):
            raise RuntimeError('SECRET_KEY must be set when APP_ENV=production.')
        app.config['SECRET_KEY'] = 'dev-only-insecure-key'
        logging.getLogger(__name__).warning('Using an insecure development SECRET_KEY. Set SECRET_KEY in .env.')

    db.init_app(app)
    init_csrf(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.fields import fields_bp
    from routes.crops import crops_bp
    from routes.workers import workers_bp
    from routes.tasks import tasks_bp
    from routes.inventory import inventory_bp
    from routes.expenses import expenses_bp
    from routes.reports import reports_bp
    from routes.copilot import copilot_bp
    from routes.smart import smart_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(fields_bp)
    app.register_blueprint(crops_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(copilot_bp)
    app.register_blueprint(smart_bp)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        msg = 'Your session security token is missing or expired. Reload the page and try again.'
        if request.is_json or request.headers.get('X-CSRF-Token'):
            return jsonify({'ok': False, 'error': msg}), 400
        return render_template('400.html', error_message=msg), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    # Auto-create database and tables on first run
    db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
    os.makedirs(db_dir, exist_ok=True)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    # Debug mode is opt-in (FLASK_DEBUG=1) and the server only listens on localhost by default.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host=os.environ.get('HOST', '127.0.0.1'), port=5000)
