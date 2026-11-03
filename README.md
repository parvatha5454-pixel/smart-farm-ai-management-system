# SmartFarm AI: Agentic Farm Management Assistant

A Flask farm management system (fields, crops, workers, tasks, inventory, expenses, reports) upgraded with an
**AI Farm Copilot** that answers questions from your real records through controlled tools, a **weekly planner**,
a **weather forecast**, and an upgraded dashboard. All original features are kept.

> **Test status (please read):** the pure-logic tests (validation, weather client, LLM client: 33 tests) were run
> and passed with `python -m unittest`. The database/route/agent tests (`tests/test_tools.py`, `test_agent.py`,
> `test_planner.py`, `test_routes.py`) were written but **could not be run** where this code was prepared, because
> Flask-SQLAlchemy could not be installed there. Run them yourself (below) before relying on this build, and expect to
> fix small issues. The UI was never opened in a browser either.

## What the AI can and cannot do
- **Can:** read your records via 8 approved tools, explain results, suggest tasks, fetch a real forecast.
- **Needs your approval:** creating a task. The AI only makes a *proposal*; nothing is saved until you click approve.
- **Cannot:** run SQL/shell/code, control irrigation equipment, send SMS/email, predict yield, or give pesticide/fertilizer doses or disease diagnoses.
- **Without an API key:** the chat shows an honest setup message. Dashboard, planner and quick data buttons still work.
- The **Weekly Planner is rule-based** (not an LLM). It works offline and explains every suggestion.

## Quick start
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then edit .env
python seed.py                    # demo data (DELETES existing data, asks first)
python app.py                     # http://127.0.0.1:5000
```
Demo logins: `admin@farm.com / admin123`, `ramesh@farm.com / worker123`.

### Configure the AI (optional)
Edit `.env`:
```
AI_API_KEY=your-key
AI_BASE_URL=https://api.openai.com/v1     # any OpenAI-compatible endpoint that supports tool calling
AI_MODEL=gpt-4o-mini
FARM_LOCATION=Madurai                      # for weather; leave empty to disable
```
Never put keys in code or commit `.env`. To use another provider, change the three values above, or add a class to
`PROVIDERS` in `services/ai/llm.py`.

## Run the tests
```bash
pip install -r requirements-dev.txt
pytest                                       # all tests
python -m unittest tests.test_validation tests.test_weather tests.test_llm   # no database needed
```
Tests never call a real AI or weather API (all mocked) and use an in-memory database.

## Upgrading an existing database
1. `python scripts/backup_db.py` (creates `database/backups/farm_<time>.db`).
2. Start the app. Three new tables are added automatically; existing tables and data are untouched.
3. To roll back, stop the app and copy the backup over `database/farm.db`.

## Deployment notes
- Set `APP_ENV=production`, a strong `SECRET_KEY`, and `SESSION_COOKIE_SECURE=1` (HTTPS only). The app refuses to start in production without `SECRET_KEY`.
- Run with a production server, e.g. `pip install gunicorn && gunicorn -w 2 app:app`. Do not use `FLASK_DEBUG=1` in production.
- SQLite is fine for a demo or one farm. Use PostgreSQL via `DATABASE_URL` for more.
- Put the app behind HTTPS (Nginx/Caddy or your host's TLS).

## Security summary
CSRF tokens on every POST, role checks on every route and tool (re-checked at approval time), input validation,
unexpected tool parameters rejected, audit log of AI tool calls, proposals and approvals (`ai_audit_log` table),
secrets from environment only, `textContent` rendering for AI output.

## Known limitations
- **Single farm:** the data model has no farm/owner field, so all admins share all records. "Each owner sees only their own farm" needs a schema change.
- The planner and AI use thresholds (e.g. "hot = 32 C, dry = under 2 mm in 3 days") that are simple assumptions, shown to the user. They are prompts to check, not agronomic advice.
- Weather uses one location from `FARM_LOCATION`, not per-field coordinates.
- AI-created tasks are unassigned; assign them from the Tasks page. Proposals cannot be edited before approval (reject and ask again).
- No rate limiting on the chat endpoint; logout is a GET link; no password reset.
- Chat quality depends on the model you configure. Small models may call tools poorly.
- Audit log has no viewer page yet (query the `ai_audit_log` table).

## Docs
- `docs/architecture.md`: assessment, diagram, safety design
- `docs/demo_script.md`: 5-minute demo
- `docs/phase1..8_*.md`: original project documentation (not updated for the AI features)

---

# Original project README (kept for reference)


A complete, beginner-friendly full-stack web application to help farmers manage fields, crops,
workers, tasks, inventory, and expenses — all from one centralized, role-based dashboard.

Built as a final-year B.Sc Computer Science project (TN Skill / SmartBridge).

---

## 📋 Project Description

The Farm Management System centralizes everyday farm record-keeping into a single secure web
application. Farm Owners (Admins) get full control over fields, crops, workers, tasks, inventory
and expenses, plus a visual dashboard and reports. Farm Workers get a focused view of their own
assigned tasks, which they can update themselves.

## ✨ Features

- Secure registration & login with hashed passwords and session-based authentication
- Two user roles: **Admin / Farm Owner** and **Farm Worker**, with role-based access control
- Full CRUD for Fields, Crops, Workers, Tasks, Inventory, and Expenses
- Automatic low-stock inventory alerts
- Interactive dashboard with 4 Chart.js visualizations
- Dedicated Reports page with summarized farm-wide statistics
- Search, filter, and delete-confirmation across all list pages
- Responsive Bootstrap 5 UI for desktop and mobile
- Custom 404 and 500 error pages
- Automatic database creation on first run
- Seed script with realistic demo data

## 🧩 Modules

1. User Authentication
2. Farm/Field Management
3. Crop Management
4. Worker Management
5. Task Management
6. Inventory Management
7. Expense Management
8. Dashboard & Reports

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| Backend | Python 3, Flask |
| Database | SQLite (via Flask-SQLAlchemy) |
| Auth | Flask sessions + Werkzeug password hashing |
| Charts | Chart.js |

## 💻 System Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Any modern web browser
- Works fully offline after dependency installation

## ⚙️ Installation Steps

```bash
# 1. Extract the project and move into the folder
cd farm_management_system

# 2. (Recommended) Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

## ▶️ How to Run

```bash
# Run the application (this also auto-creates the database and tables)
python app.py
```

Then open your browser and go to: **http://127.0.0.1:5000**

## 🌱 Database Setup & Demo Data

The SQLite database and all tables are created automatically the first time you run `app.py`.
To populate it with realistic demo data (recommended for a project demo), run:

```bash
python seed.py
```

This creates 3 fields, 5 crops, 3 user accounts (1 admin + 2 workers), 5 worker profiles,
8 tasks, 10 inventory items, and 10 expenses.

## 🔑 Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin / Farm Owner | admin@farm.com | admin123 |
| Farm Worker | ramesh@farm.com | worker123 |
| Farm Worker | lakshmi@farm.com | worker123 |

You can also register a new account directly from the app's Register page.

## 📸 Screenshots

_Add your screenshots here after running the app locally:_

- Landing Page: `screenshots/landing.png`
- Login Page: `screenshots/login.png`
- Admin Dashboard: `screenshots/dashboard-admin.png`
- Worker Dashboard: `screenshots/dashboard-worker.png`
- Fields Module: `screenshots/fields.png`
- Crops Module: `screenshots/crops.png`
- Tasks Module: `screenshots/tasks.png`
- Inventory Module: `screenshots/inventory.png`
- Reports Page: `screenshots/reports.png`

## 📁 Project Structure

```
farm_management_system/
│
├── app.py                  # Application entry point & factory
├── config.py                # Configuration (DB URI, secret key)
├── seed.py                   # Demo data seed script
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
│   └── farm.db              # Auto-generated SQLite database
│
├── models/                   # SQLAlchemy models
│   ├── user.py
│   ├── field.py
│   ├── crop.py
│   ├── worker.py
│   ├── task.py
│   ├── inventory.py
│   └── expense.py
│
├── routes/                   # Flask Blueprints (controllers)
│   ├── auth.py
│   ├── dashboard.py
│   ├── fields.py
│   ├── crops.py
│   ├── workers.py
│   ├── tasks.py
│   ├── inventory.py
│   ├── expenses.py
│   └── reports.py
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html, landing.html, login.html, register.html,
│   │   dashboard.html, profile.html, 404.html, 500.html
│   ├── fields/, crops/, workers/, tasks/, inventory/, expenses/, reports/
│
├── static/
│   ├── css/style.css
│   ├── js/script.js
│   └── images/
│
└── docs/                      # 8-Phase SmartBridge documentation
    ├── phase1_brainstorming.md
    ├── phase2_requirement_analysis.md
    ├── phase3_project_design.md
    ├── phase4_project_planning.md
    ├── phase5_project_development.md
    ├── phase6_project_testing.md
    ├── phase7_project_documentation.md
    └── phase8_project_demonstration.md
```

## 📚 Project Phases (SmartBridge 8-Phase Documentation)

All 8 required phases are documented in full inside the `docs/` folder:

1. **Brainstorming & Ideation** — problem statement, objectives, benefits, future scope
2. **Requirement Analysis** — functional/non-functional requirements, use cases
3. **Project Design** — architecture, database design, UI/navigation flow
4. **Project Planning** — timeline, task breakdown, risk management
5. **Project Development** — tech stack, implementation details
6. **Project Testing** — 34 documented test cases (positive & negative)
7. **Project Documentation** — abstract, modules, results, conclusion, references
8. **Project Demonstration** — full demo guide + voice-over script for recording

## 🔮 Future Scope

- Weather API integration for irrigation planning
- SMS/Email notifications for tasks and low stock
- Mobile app (Android/iOS) companion
- Multi-farm support for cooperative farming groups
- AI-based crop yield prediction and disease detection
- Migration to PostgreSQL/MySQL for production-scale deployment

## 📄 License

This project was created for academic/educational purposes as part of a
TN Skill / SmartBridge final-year project.

---

## Premium UI/UX redesign and smart-farming pages

All existing routes, models, roles and AI approval workflows are unchanged. New pages are additive.

| Page | URL | Who | Data source |
|---|---|---|---|
| Field overview (illustrative field cards) | `/fields/overview` | Admin | Fields, crops, irrigation log, crop observations |
| AI insights centre | `/insights` | Admin | Rule-based notes from records + forecast; optional AI briefing via the existing Copilot |
| Weather intelligence | `/weather` | All | Open-Meteo when `FARM_LOCATION` is set; clear fallback otherwise |
| Irrigation logbook | `/irrigation` | All view, Admin edit | Entries you make (no hardware control) |
| Crop health | `/crop-health` | All view and add, Admin delete | Human observations (not diagnoses) |
| Productivity analytics | `/analytics` | Admin | Chart.js on saved records |
| Farm calendar | `/calendar` | All (workers see own tasks) | Tasks, crop dates, irrigation log |

Helpers: `/api/search`, `/api/notifications`, `/api/calendar`, `/api/weather/detail` (login required).

**Honesty labels.** Every insight is tagged *Recorded* (from your data), *Estimate* (forecast or rule) or *AI-generated*.
Field health is shown only from recorded observations; if none exist it says "Not observed". The field pictures are an
illustrative layout, not a map. Inventory consumption is not tracked, so analytics shows stock vs minimum instead.
Image upload / AI image analysis is not included because the configured LLM client is text-only.

**New tables** (created automatically by `db.create_all()`): `irrigation_logs`, `crop_observations`.

**Design system:** `static/css/style.css` (tokens at the top), `static/js/script.js` (sidebar, search, notifications,
toasts, confirm dialog, validation, table filters), `templates/_macros.html` (KPI cards, badges, empty states).

Run the tests with `python -m pytest` (120 tests).
