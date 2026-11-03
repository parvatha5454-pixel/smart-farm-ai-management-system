# Phase 8 – Project Demonstration Guide

## 1. Project Name
Farm Management System

## 2. Introduction
A full-stack web application built with Flask, SQLite, and Bootstrap 5 that helps farmers
manage fields, crops, workers, tasks, inventory, and expenses from one centralized dashboard.

## 3. Purpose
To digitize and simplify day-to-day farm record-keeping, replacing manual/paper-based tracking
with a secure, role-based, visual web application.

## 4. Problem Solved
Farmers previously lacked a single place to track farm operations, leading to missed tasks,
inventory shortages, and unclear expense visibility. This system solves that with centralized,
real-time records and alerts.

## 5. Main Modules
1. User Authentication (Admin/Worker roles)
2. Field Management
3. Crop Management
4. Worker Management
5. Task Management
6. Inventory Management (with low-stock alerts)
7. Expense Management
8. Dashboard & Reports (Chart.js visualizations)

## 6. Login Demonstration
- Show the landing page → click Login.
- Log in as Admin (`admin@farm.com` / `admin123`) → land on Admin Dashboard.
- Log out, then log in as Worker (`ramesh@farm.com` / `worker123`) → land on Worker Dashboard.
- Point out that the navigation menu changes based on role.

## 7. Dashboard Demonstration
- As Admin: show the 6 stat cards (Fields, Crops, Workers, Tasks, Expenses, Low Stock) and
  the 4 Chart.js visualizations (Expense by Category, Crop Status, Task Status, Monthly Expenses).
- As Worker: show the simplified task-focused dashboard.

## 8. Add Field Demonstration
- Navigate to Fields → Add Field.
- Fill in name, location, area, soil type, irrigation type → Save.
- Show the new field appearing in the list, then open its detail view.

## 9. Add Crop Demonstration
- Navigate to Crops → Add Crop.
- Select a field, enter planting date, status, quantity → Save.
- Show status filter and search working on the crop list.

## 10. Worker Management
- Navigate to Workers → Add Worker.
- Enter contact details, role, and joining date → Save.
- Show the worker's detail page listing their assigned tasks.

## 11. Task Management
- Navigate to Tasks → Add Task, assign to a worker with a due date and priority.
- Switch to the Worker's login and show them updating the task's status from the dropdown.
- Switch back to Admin and show the status change reflected instantly.

## 12. Inventory Management
- Navigate to Inventory → Add Item with a quantity below the minimum stock level.
- Show the "Low Stock" badge appearing automatically and the dashboard alert updating.

## 13. Expense Management
- Navigate to Expenses → Add Expense with a category, amount, date, and payment method.
- Show the running total at the bottom of the expense list.

## 14. Reports/Charts
- Navigate to Reports.
- Walk through the summarized totals and the category/status breakdown tables.

## 15. Final Output
A working, role-based, full-stack Farm Management System with 7+ functional modules, data
visualization, validation, and security best practices — ready to run locally or deploy.

## 16. Benefits
- Saves time and reduces errors versus manual tracking.
- Improves transparency between farm owners and workers.
- Provides early warning for inventory shortages.
- Supports better financial decision-making through expense visibility.

## 17. Future Scope
- SMS/Email alerts, weather integration, mobile app, multi-farm support, and AI-based crop
  disease detection (see Phase 7 for full details).

---

## Voice-Over Script (for screen recording)

"Hi, and welcome to my final-year project demonstration — the Farm Management System.

This is a full-stack web application built using Python, Flask, and SQLite, designed to help
farmers manage their day-to-day operations from a single dashboard.

Let's start on the landing page. From here, users can register or log in. I'll log in as the
Admin, or Farm Owner. Once logged in, I land on the Dashboard, which shows key statistics —
total fields, active crops, workers, pending tasks, total expenses, and any low-stock inventory
alerts — along with four interactive charts powered by Chart.js.

Let's look at Field Management. I can add a new field with its location, area, soil type, and
irrigation type. Once saved, it appears in the field list, where I can view, edit, or delete it.

Next, Crop Management lets me add crops linked to a specific field, track their planting and
harvest dates, and update their status as they move from Planned to Growing to Harvested.

In Worker Management, I can add farm workers with their contact details and job role. Each
worker can optionally have their own login account.

Now, Task Management — I'll assign a task to a worker with a due date and priority. If I log in
as that worker, I can see only my assigned tasks and update their status myself, without needing
full admin access.

Inventory Management tracks farm supplies like seeds, fertilizers, and equipment. If any item
falls below its minimum stock level, the system automatically flags it as Low Stock, both in the
inventory list and on the main dashboard.

Expense Management lets me log every farm expense by category, with a running total always
visible.

Finally, the Reports page brings everything together with summarized totals and category
breakdowns for a complete view of farm performance.

That concludes my demonstration of the Farm Management System. Thank you for watching."
