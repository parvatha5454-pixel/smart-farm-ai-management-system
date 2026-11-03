import os
import tempfile
from datetime import date, timedelta

# Importing `app` creates a module-level app, so point it at a throwaway DB first.
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "import_time.db")
os.environ["AI_API_KEY"] = ""

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from models.crop import Crop  # noqa: E402
from models.expense import Expense  # noqa: E402
from models.field import Field  # noqa: E402
from models.inventory import InventoryItem  # noqa: E402
from models.task import Task  # noqa: E402
from models.user import User  # noqa: E402
from models.worker import Worker  # noqa: E402
from services import weather  # noqa: E402
from services.ai.tools import UserCtx  # noqa: E402


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://", "CSRF_ENABLED": False,
                      "AI_API_KEY": "", "FARM_LOCATION": "", "SECRET_KEY": "test-secret"})
    weather.clear_cache()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def data(app):
    """Small known dataset. Returns a dict of useful objects/ids."""
    today = date.today()
    admin = User(full_name="Owner", email="owner@test.com", role="admin")
    admin.set_password("pw123456")
    w1 = User(full_name="Worker One", email="w1@test.com", role="worker")
    w1.set_password("pw123456")
    w2 = User(full_name="Worker Two", email="w2@test.com", role="worker")
    w2.set_password("pw123456")
    db.session.add_all([admin, w1, w2])
    db.session.commit()

    wp1 = Worker(name="Worker One", user_id=w1.id)
    wp2 = Worker(name="Worker Two", user_id=w2.id)
    db.session.add_all([wp1, wp2])

    f1 = Field(name="North", area=2.0, soil_type="Loamy", irrigation_type="Drip")
    f2 = Field(name="South", area=1.0)  # no irrigation type, no crops
    db.session.add_all([f1, f2])
    db.session.commit()

    db.session.add_all([
        Crop(name="Tomato", field_id=f1.id, planting_date=today - timedelta(days=60),
             expected_harvest_date=today + timedelta(days=5), status="Growing"),
        Crop(name="Chilli", field_id=f1.id, planting_date=today - timedelta(days=10), status="Growing"),
    ])
    db.session.add_all([
        Expense(category="Seeds", amount=100.0, date=date(2025, 1, 5)),
        Expense(category="Seeds", amount=50.5, date=date(2025, 1, 31)),
        Expense(category="Labour", amount=200.0, date=date(2025, 1, 15)),
        Expense(category="Labour", amount=999.0, date=date(2025, 2, 1)),   # outside range
        Expense(category="Other", amount=5.0, date=date(2024, 12, 31)),    # outside range
    ])
    db.session.add_all([
        InventoryItem(name="Urea", quantity=2, unit="kg", minimum_stock_level=10),
        InventoryItem(name="Seeds", quantity=50, unit="kg", minimum_stock_level=10),
        InventoryItem(name="Spade", quantity=0, unit="units", minimum_stock_level=0),  # no minimum -> no alert
    ])
    db.session.commit()

    db.session.add_all([
        Task(title="Water tomatoes", worker_id=wp1.id, assigned_to=w1.id, status="Pending",
             due_date=today + timedelta(days=1), priority="High"),
        Task(title="Old task", worker_id=wp1.id, assigned_to=w1.id, status="Pending",
             due_date=today - timedelta(days=3), priority="Low"),
        Task(title="Done task", worker_id=wp1.id, assigned_to=w1.id, status="Completed",
             due_date=today - timedelta(days=9), priority="Low"),
        Task(title="Other worker task", worker_id=wp2.id, assigned_to=w2.id, status="In Progress",
             due_date=today + timedelta(days=2), priority="Medium"),
    ])
    db.session.commit()
    return {"admin": admin, "w1": w1, "w2": w2, "today": today,
            "admin_ctx": UserCtx(admin.id, "admin", "Owner"),
            "w1_ctx": UserCtx(w1.id, "worker", "Worker One"),
            "w2_ctx": UserCtx(w2.id, "worker", "Worker Two")}


@pytest.fixture
def client_factory(app):
    return app.test_client
