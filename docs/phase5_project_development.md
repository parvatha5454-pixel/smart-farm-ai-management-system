# Phase 5 – Project Development

## Technology Stack
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js
- **Backend:** Python 3, Flask, Flask-SQLAlchemy
- **Database:** SQLite
- **Authentication:** Flask sessions + Werkzeug password hashing

## Folder Structure
```
farm_management_system/
├── app.py
├── config.py
├── seed.py
├── requirements.txt
├── README.md
├── .gitignore
├── database/farm.db          (auto-generated on first run)
├── models/                   (SQLAlchemy models)
├── routes/                   (Flask Blueprints)
├── templates/                (Jinja2 HTML templates)
├── static/css, static/js     (styling and client-side scripts)
└── docs/                     (8-phase documentation)
```

## Database Implementation
- `Config.SQLALCHEMY_DATABASE_URI` points to `database/farm.db`.
- `db.create_all()` is called inside `create_app()` so the database and tables are created
  automatically the first time the app runs — no manual setup required.
- `seed.py` populates realistic demo data (3 fields, 5 crops, 5 workers, 8 tasks,
  10 inventory items, 10 expenses) for demonstration purposes.

## Backend Implementation
- Each module has its own Blueprint file in `routes/` with GET/POST handlers for
  list, add, edit, view, and delete operations.
- Two decorators — `login_required` and `admin_required` — enforce role-based access
  control on every protected route.
- All forms are validated server-side before touching the database.

## Frontend Implementation
- `templates/base.html` provides the shared navbar, flash-message area, and footer.
- Bootstrap 5 utility classes provide the responsive grid, cards, tables, and forms.
- Font Awesome icons are used throughout for visual clarity.
- Chart.js renders four dashboard charts using data serialized from Flask into
  JSON via Jinja's `tojson` filter.

## Authentication
- Passwords are hashed using Werkzeug's `generate_password_hash` / `check_password_hash`.
- On successful login, `user_id`, `full_name`, and `role` are stored in the Flask session.
- `session.permanent = True` combined with `PERMANENT_SESSION_LIFETIME` controls session expiry.

## Module Implementation
Each of the 8 modules (Auth, Fields, Crops, Workers, Tasks, Inventory, Expenses,
Dashboard & Reports) was implemented as a self-contained Blueprint with its own
templates folder, following an identical list/add/edit/(view)/delete pattern for consistency.

## Screenshots
_Add screenshots here after running the application locally:_
- [ ] Landing Page
- [ ] Login Page
- [ ] Admin Dashboard with charts
- [ ] Worker Dashboard
- [ ] Fields list & form
- [ ] Crops list & form
- [ ] Workers list & form
- [ ] Tasks list & form
- [ ] Inventory list with low-stock badges
- [ ] Expenses list
- [ ] Reports page

## Development Steps (Summary)
1. Scaffolded project folders and configuration.
2. Implemented all SQLAlchemy models with relationships.
3. Built authentication with hashing and session management.
4. Implemented each functional module (routes + templates) in sequence.
5. Built the dashboard with aggregated SQL queries and Chart.js visualizations.
6. Wrote the seed script for demo data.
7. Performed manual testing across all modules and fixed identified issues.
8. Wrote full documentation and packaged the project as a ZIP file.
