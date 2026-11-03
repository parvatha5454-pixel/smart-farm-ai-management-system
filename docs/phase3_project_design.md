# Phase 3 – Project Design

## System Architecture
The application follows the **MVC-inspired (Model-View-Controller)** pattern using Flask's
Blueprint system:

- **Models** (`models/`) — SQLAlchemy ORM classes representing database tables.
- **Views/Templates** (`templates/`) — Jinja2 HTML templates rendered to the browser.
- **Controllers** (`routes/`) — Flask Blueprints containing route handlers (business logic).

```
Browser (HTML/Bootstrap/JS)
        |
        v
Flask App (app.py) --> Blueprints (routes/*.py) --> Models (models/*.py) --> SQLite (database/farm.db)
        |
        v
Jinja2 Templates (templates/*.html)
```

## Module Design
| Module | Blueprint | Responsibility |
|---|---|---|
| Authentication | auth_bp | Register, login, logout, session/profile |
| Dashboard | dashboard_bp | Role-based stats and charts |
| Fields | fields_bp | Field CRUD |
| Crops | crops_bp | Crop CRUD (linked to fields) |
| Workers | workers_bp | Worker CRUD |
| Tasks | tasks_bp | Task CRUD + worker status updates |
| Inventory | inventory_bp | Inventory CRUD + low-stock detection |
| Expenses | expenses_bp | Expense CRUD |
| Reports | reports_bp | Aggregated summaries |

## Database Design (Entity Overview)
- **users** (id, full_name, email, password_hash, role, phone, created_at)
- **fields** (id, name, location, area, soil_type, irrigation_type, created_at)
- **crops** (id, name, field_id → fields.id, planting_date, expected_harvest_date, status, quantity, notes, created_at)
- **workers** (id, name, phone, email, address, role, joining_date, user_id → users.id, created_at)
- **tasks** (id, title, description, worker_id → workers.id, assigned_to → users.id, due_date, priority, status, created_at)
- **inventory** (id, name, category, quantity, unit, minimum_stock_level, purchase_date, supplier, cost, created_at)
- **expenses** (id, category, amount, date, description, payment_method, created_by → users.id, created_at)

## ER Diagram Description
- One **Field** has many **Crops** (1:N).
- One **Worker** has many **Tasks** (1:N).
- One **User** may optionally correspond to one **Worker** profile (1:1, via `worker.user_id`).
- One **User** can create many **Expenses** (1:N, via `expenses.created_by`).
- **Tasks** optionally reference the assigned user's login account directly (`assigned_to`).

## Data Flow Description
1. User submits a login form → `auth.py` validates credentials → session created.
2. Admin submits an "Add Crop" form → `crops.py` validates input → new row inserted via SQLAlchemy → redirect to crop list.
3. Worker updates a task status → `tasks.py` checks ownership → updates row → redirect to task list.
4. Dashboard route aggregates counts/sums via SQLAlchemy queries → passed to Chart.js in the template.

## UI Design Description
- Bootstrap 5 navbar with role-based menu items.
- Card-based statistic tiles on the dashboard.
- Bootstrap tables with search/filter forms for list pages.
- Modal-free, confirm()-based delete confirmation for simplicity.
- Consistent green/farm-themed color palette across all pages.

## Navigation Flow
```
Landing Page → Login/Register → Dashboard
Dashboard → Fields / Crops / Workers / Tasks / Inventory / Expenses / Reports
Each list page → Add/Edit/View/Delete sub-pages → back to list page
```
