import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load variables from a local .env file if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:  # python-dotenv is optional
    pass


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    # "development" (default) or "production". Production REQUIRES SECRET_KEY.
    APP_ENV = os.environ.get('APP_ENV', 'development')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'database', 'farm.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 hours

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'

    # CSRF protection for all state-changing requests
    CSRF_ENABLED = True

    # ---- AI provider (any OpenAI-compatible chat-completions API) ----
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai_compatible')
    AI_API_KEY = os.environ.get('AI_API_KEY', '')
    AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1')
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4o-mini')
    AI_TIMEOUT_SECONDS = _int('AI_TIMEOUT_SECONDS', 30)
    AI_MAX_STEPS = _int('AI_MAX_STEPS', 5)

    # ---- Weather (Open-Meteo, no API key needed) ----
    # City/town name used for forecasts, e.g. "Madurai". Leave empty to disable.
    FARM_LOCATION = os.environ.get('FARM_LOCATION', '')
    WEATHER_TIMEOUT_SECONDS = _int('WEATHER_TIMEOUT_SECONDS', 6)
