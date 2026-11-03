# Phase 2 – Requirement Analysis

## Functional Requirements
1. Users can register and log in with role selection (Admin/Worker).
2. Passwords must be securely hashed; sessions manage login state.
3. Admins can perform full CRUD on Fields, Crops, Workers, Tasks, Inventory, and Expenses.
4. Workers can view their assigned tasks and update task status.
5. Workers can view crop and basic farm information (read-only).
6. The system must display a dashboard with key farm statistics and charts.
7. The Reports page must summarize farm data for Admins.
8. Unauthorized users must be redirected away from restricted pages.
9. Inventory items must show a "low stock" warning when quantity falls below the minimum threshold.
10. All forms must validate required fields, numeric fields, dates, and emails.

## Non-Functional Requirements
- **Usability:** Simple, clean UI understandable by non-technical farm owners.
- **Performance:** Pages should load quickly with SQLite for small-to-medium datasets.
- **Security:** Passwords hashed, sessions protected, SQL injection prevented via ORM.
- **Portability:** Must run fully offline on any machine with Python installed.
- **Maintainability:** Modular code structure (models/routes/templates) for easy extension.
- **Responsiveness:** UI must adapt to desktop, tablet, and mobile screens.

## Hardware Requirements
- Minimum: 4 GB RAM, dual-core processor, 500 MB free disk space.
- Recommended: 8 GB RAM for smooth local development.

## Software Requirements
- Python 3.9 or higher
- Flask, Flask-SQLAlchemy, Werkzeug (see requirements.txt)
- SQLite (bundled with Python)
- Modern web browser (Chrome, Firefox, Edge)
- Code editor (VS Code recommended)

## User Requirements
- Farm Owner needs visibility into all farm operations at a glance.
- Farm Worker needs a simple way to see and update assigned work without needing full system access.

## System Requirements
- A running Flask development server (or production WSGI server for deployment).
- A writable `database/` directory for the SQLite file.

## Use Cases
| Use Case | Actor | Description |
|---|---|---|
| Register Account | Admin/Worker | Create a new account with a selected role |
| Login | Admin/Worker | Authenticate and start a session |
| Manage Fields | Admin | Add/edit/delete/view field records |
| Manage Crops | Admin | Add/edit/delete/view crop records linked to fields |
| Manage Workers | Admin | Add/edit/delete/view worker records |
| Assign Task | Admin | Create a task and assign it to a worker |
| Update Task Status | Worker | Change status of an assigned task |
| Manage Inventory | Admin | Track stock items and get low-stock alerts |
| Record Expense | Admin | Log farm expenses by category |
| View Dashboard | Admin/Worker | View role-appropriate statistics and charts |
| View Reports | Admin | View summarized farm-wide reports |
