"""
Seed script for Farm Management System.
Populates the database with realistic demo data for project demonstration.
Run with: python seed.py
"""
import sys
from datetime import date, timedelta
from app import create_app
from models import db
from models.user import User
from models.field import Field
from models.crop import Crop
from models.worker import Worker
from models.task import Task
from models.inventory import InventoryItem
from models.expense import Expense
from models.farm_ops import CropObservation, IrrigationLog

app = create_app()

with app.app_context():
    if User.query.count() > 0 and '--yes' not in sys.argv:
        print("WARNING: this database already has data. seed.py DELETES all farm records and replaces them with demo data.")
        print("Back up first:  python scripts/backup_db.py")
        if input("Type YES to continue: ").strip() != "YES":
            print("Cancelled. Nothing was changed.")
            sys.exit(0)
    print("Clearing existing data...")
    CropObservation.query.delete()
    IrrigationLog.query.delete()
    Task.query.delete()
    Crop.query.delete()
    Expense.query.delete()
    InventoryItem.query.delete()
    Worker.query.delete()
    Field.query.delete()
    User.query.delete()
    db.session.commit()

    print("Creating users...")
    admin = User(full_name="Suresh Kumar", email="admin@farm.com", role="admin", phone="9876543210")
    admin.set_password("admin123")

    worker_user_1 = User(full_name="Ramesh Babu", email="ramesh@farm.com", role="worker", phone="9876500011")
    worker_user_1.set_password("worker123")

    worker_user_2 = User(full_name="Lakshmi Devi", email="lakshmi@farm.com", role="worker", phone="9876500022")
    worker_user_2.set_password("worker123")

    db.session.add_all([admin, worker_user_1, worker_user_2])
    db.session.commit()

    print("Creating fields...")
    field1 = Field(name="North Paddy Field", location="Sector A, Village Road", area=5.5,
                    soil_type="Alluvial", irrigation_type="Canal")
    field2 = Field(name="South Vegetable Plot", location="Sector B, Near Pond", area=2.25,
                    soil_type="Loamy", irrigation_type="Drip")
    field3 = Field(name="East Sugarcane Field", location="Sector C, Highway Side", area=8.0,
                    soil_type="Black", irrigation_type="Flood")
    db.session.add_all([field1, field2, field3])
    db.session.commit()

    print("Creating crops...")
    today = date.today()
    crops = [
        Crop(name="Basmati Rice", field_id=field1.id, planting_date=today - timedelta(days=60),
             expected_harvest_date=today + timedelta(days=45), status="Growing", quantity=0,
             notes="High-yield variety, monitor for pests."),
        Crop(name="Tomato", field_id=field2.id, planting_date=today - timedelta(days=30),
             expected_harvest_date=today + timedelta(days=20), status="Growing", quantity=0,
             notes="Requires regular drip irrigation."),
        Crop(name="Sugarcane", field_id=field3.id, planting_date=today - timedelta(days=200),
             expected_harvest_date=today + timedelta(days=100), status="Growing", quantity=0,
             notes="Long duration crop."),
        Crop(name="Wheat", field_id=field1.id, planting_date=today - timedelta(days=120),
             expected_harvest_date=today - timedelta(days=5), status="Ready for Harvest", quantity=1200,
             notes="Ready for harvesting this week."),
        Crop(name="Onion", field_id=field2.id, planting_date=today - timedelta(days=90),
             expected_harvest_date=today - timedelta(days=10), status="Harvested", quantity=800,
             notes="Harvested and stored in warehouse."),
    ]
    db.session.add_all(crops)
    db.session.commit()

    print("Creating workers...")
    workers = [
        Worker(name="Ramesh Babu", phone="9876500011", email="ramesh@farm.com",
               address="12, Farmer Colony", role="Field Supervisor",
               joining_date=today - timedelta(days=400), user_id=worker_user_1.id),
        Worker(name="Lakshmi Devi", phone="9876500022", email="lakshmi@farm.com",
               address="45, Village Street", role="Irrigation Specialist",
               joining_date=today - timedelta(days=300), user_id=worker_user_2.id),
        Worker(name="Muthu Raman", phone="9876500033", email="muthu@example.com",
               address="7, Temple Road", role="Field Laborer",
               joining_date=today - timedelta(days=250)),
        Worker(name="Kavya Priya", phone="9876500044", email="kavya@example.com",
               address="21, Market Street", role="Harvest Coordinator",
               joining_date=today - timedelta(days=150)),
        Worker(name="Arun Kumar", phone="9876500055", email="arun@example.com",
               address="9, School Lane", role="Equipment Operator",
               joining_date=today - timedelta(days=90)),
    ]
    db.session.add_all(workers)
    db.session.commit()

    print("Creating tasks...")
    tasks = [
        Task(title="Apply fertilizer to Rice field", description="Apply urea fertilizer as per schedule.",
             worker_id=workers[0].id, assigned_to=worker_user_1.id, due_date=today + timedelta(days=2),
             priority="High", status="Pending"),
        Task(title="Check drip irrigation lines", description="Inspect and repair any leaks in Sector B.",
             worker_id=workers[1].id, assigned_to=worker_user_2.id, due_date=today + timedelta(days=1),
             priority="High", status="In Progress"),
        Task(title="Weed removal in Vegetable Plot", description="Manual weeding required.",
             worker_id=workers[2].id, due_date=today + timedelta(days=3),
             priority="Medium", status="Pending"),
        Task(title="Harvest Wheat crop", description="Coordinate harvesting team and equipment.",
             worker_id=workers[3].id, due_date=today + timedelta(days=1),
             priority="High", status="Pending"),
        Task(title="Service tractor", description="Routine maintenance and oil change.",
             worker_id=workers[4].id, due_date=today + timedelta(days=5),
             priority="Low", status="Pending"),
        Task(title="Sugarcane pest inspection", description="Check for stem borer infestation.",
             worker_id=workers[0].id, assigned_to=worker_user_1.id, due_date=today - timedelta(days=2),
             priority="Medium", status="Completed"),
        Task(title="Store harvested Onion", description="Move onion stock to warehouse.",
             worker_id=workers[3].id, due_date=today - timedelta(days=8),
             priority="Medium", status="Completed"),
        Task(title="Update irrigation schedule", description="Plan next week's irrigation cycle.",
             worker_id=workers[1].id, assigned_to=worker_user_2.id, due_date=today + timedelta(days=4),
             priority="Low", status="In Progress"),
    ]
    db.session.add_all(tasks)
    db.session.commit()

    print("Creating inventory items...")
    inventory_items = [
        InventoryItem(name="Basmati Rice Seeds", category="Seeds", quantity=50, unit="kg",
                       minimum_stock_level=20, purchase_date=today - timedelta(days=70),
                       supplier="AgriSeeds Co.", cost=4500),
        InventoryItem(name="Tomato Seedlings", category="Seeds", quantity=5, unit="trays",
                       minimum_stock_level=10, purchase_date=today - timedelta(days=35),
                       supplier="Green Nursery", cost=1200),
        InventoryItem(name="Urea Fertilizer", category="Fertilizers", quantity=200, unit="kg",
                       minimum_stock_level=50, purchase_date=today - timedelta(days=20),
                       supplier="National Fertilizers Ltd.", cost=3200),
        InventoryItem(name="DAP Fertilizer", category="Fertilizers", quantity=15, unit="kg",
                       minimum_stock_level=30, purchase_date=today - timedelta(days=15),
                       supplier="National Fertilizers Ltd.", cost=1800),
        InventoryItem(name="Pesticide Spray (Neem-based)", category="Pesticides", quantity=25, unit="liters",
                       minimum_stock_level=10, purchase_date=today - timedelta(days=25),
                       supplier="EcoAgro Solutions", cost=2200),
        InventoryItem(name="Insecticide", category="Pesticides", quantity=8, unit="liters",
                       minimum_stock_level=10, purchase_date=today - timedelta(days=40),
                       supplier="EcoAgro Solutions", cost=1600),
        InventoryItem(name="Hand Tools Set", category="Tools", quantity=12, unit="units",
                       minimum_stock_level=5, purchase_date=today - timedelta(days=200),
                       supplier="Farm Hardware Store", cost=6000),
        InventoryItem(name="Sprinkler Heads", category="Tools", quantity=30, unit="units",
                       minimum_stock_level=15, purchase_date=today - timedelta(days=100),
                       supplier="IrriTech Supplies", cost=4500),
        InventoryItem(name="Tractor", category="Equipment", quantity=1, unit="units",
                       minimum_stock_level=1, purchase_date=today - timedelta(days=800),
                       supplier="Mahindra Tractors", cost=650000),
        InventoryItem(name="Water Pump", category="Equipment", quantity=2, unit="units",
                       minimum_stock_level=1, purchase_date=today - timedelta(days=500),
                       supplier="AquaFlow Pumps", cost=45000),
    ]
    db.session.add_all(inventory_items)
    db.session.commit()

    print("Creating expenses...")
    expenses = [
        Expense(category="Seeds", amount=4500, date=today - timedelta(days=70),
                description="Purchase of Basmati rice seeds", payment_method="Bank Transfer", created_by=admin.id),
        Expense(category="Seeds", amount=1200, date=today - timedelta(days=35),
                description="Tomato seedlings from nursery", payment_method="Cash", created_by=admin.id),
        Expense(category="Fertilizer", amount=3200, date=today - timedelta(days=20),
                description="Urea fertilizer bulk purchase", payment_method="UPI", created_by=admin.id),
        Expense(category="Fertilizer", amount=1800, date=today - timedelta(days=15),
                description="DAP fertilizer restock", payment_method="UPI", created_by=admin.id),
        Expense(category="Labour", amount=8000, date=today - timedelta(days=10),
                description="Monthly wages for field laborers", payment_method="Bank Transfer", created_by=admin.id),
        Expense(category="Labour", amount=7500, date=today - timedelta(days=40),
                description="Wages for harvesting season", payment_method="Cash", created_by=admin.id),
        Expense(category="Equipment", amount=15000, date=today - timedelta(days=60),
                description="Tractor servicing and repair", payment_method="Card", created_by=admin.id),
        Expense(category="Irrigation", amount=4500, date=today - timedelta(days=100),
                description="Sprinkler head replacements", payment_method="UPI", created_by=admin.id),
        Expense(category="Transportation", amount=2500, date=today - timedelta(days=8),
                description="Transport of harvested onions to market", payment_method="Cash", created_by=admin.id),
        Expense(category="Other", amount=1000, date=today - timedelta(days=5),
                description="Miscellaneous farm supplies", payment_method="Cash", created_by=admin.id),
    ]
    db.session.add_all(expenses)
    db.session.commit()

    print("\n✅ Database seeded successfully!")
    print("\nDemo login credentials:")
    print("  Admin  : admin@farm.com / admin123")
    print("  Worker : ramesh@farm.com / worker123")
    print("  Worker : lakshmi@farm.com / worker123")
