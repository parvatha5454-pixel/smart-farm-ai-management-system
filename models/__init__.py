from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models so they register with SQLAlchemy metadata
from models.user import User
from models.field import Field
from models.crop import Crop
from models.worker import Worker
from models.task import Task
from models.inventory import InventoryItem
from models.expense import Expense
from models.ai import AuditLog, ChatMessage, PendingAction
from models.farm_ops import IrrigationLog, CropObservation
