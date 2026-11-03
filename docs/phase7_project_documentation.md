# Phase 7 – Project Documentation

## Project Abstract
The Farm Management System is a full-stack web application designed to help farmers and farm
owners digitally manage their day-to-day agricultural operations. It consolidates field, crop,
worker, task, inventory, and expense records into a single, secure, role-based platform, replacing
error-prone manual and paper-based tracking methods with an easy-to-use, visual, data-driven system.

## Introduction
Modern farm operations involve managing multiple interdependent resources — land, crops, labor,
supplies, and money — often without a unified system to track them. This project applies standard
web development practices (Flask, SQLAlchemy, Bootstrap) to build a practical, beginner-friendly
tool that a small farm could realistically use, while also serving as a comprehensive final-year
academic project demonstrating full CRUD operations, authentication, authorization, and data
visualization.

## Problem Statement
Farmers lack an affordable, simple, centralized system to track fields, crops, labor, inventory,
and expenses, resulting in inefficiencies, missed tasks, and poor financial visibility.

## Objectives
- Centralize farm record-keeping in one web application.
- Enforce secure, role-based access for Admins and Workers.
- Provide visual dashboards for quick decision-making.
- Alert on low inventory before stock-outs occur.
- Keep the system lightweight and fully functional offline.

## Existing System
Most small farms rely on notebooks, spreadsheets, or verbal communication to track field activity,
worker assignments, and expenses. This is slow, error-prone, and offers no analytics or alerts.

## Proposed System
A Flask-based web application with:
- Secure authentication and two user roles (Admin, Worker)
- Full CRUD modules for Fields, Crops, Workers, Tasks, Inventory, and Expenses
- A visual dashboard (Chart.js) and a dedicated Reports page
- Automatic low-stock inventory alerts
- Responsive Bootstrap 5 UI for desktop and mobile use

## Modules
1. User Authentication
2. Farm/Field Management
3. Crop Management
4. Worker Management
5. Task Management
6. Inventory Management
7. Expense Management
8. Dashboard & Reports

## Technologies
- Python 3, Flask, Flask-SQLAlchemy, Werkzeug
- SQLite database
- HTML5, CSS3, Bootstrap 5, JavaScript, Chart.js
- Font Awesome icons

## Database
SQLite database (`farm.db`) with 7 relational tables: `users`, `fields`, `crops`, `workers`,
`tasks`, `inventory`, `expenses` — connected via foreign keys (Field→Crop, Worker→Task,
User→Worker, User→Expense).

## Implementation
The application follows a modular Flask Blueprint architecture. Each functional module has
its own model, route file, and set of templates, all sharing a common base layout and a
consistent CRUD interaction pattern. See Phase 5 for implementation details.

## Testing
34 manual test cases were executed covering both positive and negative scenarios across every
module, including authentication, authorization, validation, and security checks. See Phase 6
for the full test case matrix.

## Results
The system successfully allows an Admin to manage all farm resources and a Worker to manage
their own tasks, with real-time dashboard statistics, functioning low-stock alerts, and
accurate expense/crop/task summaries in the Reports page.

## Advantages
- Centralized, single source of truth for farm data.
- Role-based access keeps sensitive management functions restricted to Admins.
- Visual dashboard makes trends easy to spot at a glance.
- Fully offline-capable after initial setup — no internet dependency.
- Simple, modular codebase that is easy to extend or maintain.

## Limitations
- Single-farm design; does not yet support multiple farms per Admin account.
- No real-time notifications (email/SMS) for tasks or low stock.
- SQLite is suitable for small-to-medium data volumes, not high-concurrency production use.
- No weather or market-price integration in the current version.

## Future Enhancements
- Multi-farm and multi-tenant support.
- Email/SMS notifications for due tasks and low stock.
- Weather API integration for irrigation scheduling.
- Mobile app (Android/iOS) companion.
- AI-based crop disease detection from photos.
- Migration path to PostgreSQL/MySQL for larger deployments.

## Conclusion
The Farm Management System demonstrates a complete, practical application of full-stack web
development concepts — authentication, role-based authorization, relational database design,
CRUD operations, data visualization, and responsive UI design — applied to a real-world domain.
It is ready for local demonstration, GitHub publication, and further extension.

## References
- Flask Documentation — https://flask.palletsprojects.com/
- Flask-SQLAlchemy Documentation — https://flask-sqlalchemy.palletsprojects.com/
- Bootstrap 5 Documentation — https://getbootstrap.com/docs/5.3/
- Chart.js Documentation — https://www.chartjs.org/docs/latest/
- Werkzeug Security Documentation — https://werkzeug.palletsprojects.com/en/latest/utils/#module-werkzeug.security
