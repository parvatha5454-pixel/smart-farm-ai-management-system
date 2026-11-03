"""Lightweight session-based CSRF protection for every state-changing request."""
import hmac
import secrets

from flask import abort, request, session


def get_csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def init_csrf(app):
    app.jinja_env.globals["csrf_token"] = get_csrf_token

    @app.before_request
    def _verify_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            expected = session.get("_csrf", "")
            if not expected or not sent or not hmac.compare_digest(sent, expected):
                abort(400)
