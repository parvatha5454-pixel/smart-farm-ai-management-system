# Phase 6 – Project Testing

## Test Case Document

| Test Case ID | Module | Test Scenario | Input | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|---|
| TC01 | Authentication | Register with valid details | Valid name, email, password (≥6 chars), matching confirm password | Account created, redirected to login | As expected | Pass |
| TC02 | Authentication | Register with duplicate email | Email already in `users` table | Error: "An account with that email already exists." | As expected | Pass |
| TC03 | Authentication | Register with mismatched passwords | password ≠ confirm_password | Error: "Passwords do not match." | As expected | Pass |
| TC04 | Authentication | Register with short password | Password with < 6 characters | Error: "Password must be at least 6 characters long." | As expected | Pass |
| TC05 | Authentication | Login with correct credentials | Valid email + password | Session created, redirected to Dashboard | As expected | Pass |
| TC06 | Authentication | Login with wrong password | Valid email, wrong password | Error: "Invalid email or password." | As expected | Pass |
| TC07 | Authentication | Access dashboard without login | Navigate to `/dashboard` while logged out | Redirected to login page with warning | As expected | Pass |
| TC08 | Authentication | Logout | Click Logout | Session cleared, redirected to login | As expected | Pass |
| TC09 | Authorization | Worker accesses admin-only page | Worker logs in, navigates to `/fields` | Redirected to dashboard with "permission" error | As expected | Pass |
| TC10 | Field Management | Add field with valid data | Name, positive area, soil type, irrigation type | Field created, appears in list | As expected | Pass |
| TC11 | Field Management | Add field with negative area | Area = -5 | Error: "Area must be a positive number." | As expected | Pass |
| TC12 | Field Management | Add field with missing name | Name left blank | Error: "Field name is required." | As expected | Pass |
| TC13 | Field Management | Edit existing field | Update location and soil type | Field updated successfully | As expected | Pass |
| TC14 | Field Management | Delete field with linked crops | Delete a field that has crops | Field and its crops removed (cascade) | As expected | Pass |
| TC15 | Crop Management | Add crop with valid data | Name, field, planting date, valid status | Crop created and listed | As expected | Pass |
| TC16 | Crop Management | Add crop with negative quantity | Quantity = -10 | Error: "Quantity cannot be negative." | As expected | Pass |
| TC17 | Crop Management | Add crop without selecting field | Field not selected | Error: "Please select a field." | As expected | Pass |
| TC18 | Crop Management | Filter crops by status | Select "Harvested" from filter | Only harvested crops shown | As expected | Pass |
| TC19 | Worker Management | Add worker with valid data | Name, phone, joining date | Worker created and listed | As expected | Pass |
| TC20 | Worker Management | Add worker with invalid email | email = "notanemail" | Error: "Please enter a valid email address." | As expected | Pass |
| TC21 | Worker Management | Delete worker with assigned tasks | Delete worker with active tasks | Worker and their tasks removed (cascade) | As expected | Pass |
| TC22 | Task Management | Assign task to worker | Title, worker, due date, priority | Task created and appears in task list | As expected | Pass |
| TC23 | Task Management | Worker updates own task status | Worker changes status dropdown | Status updated, persists after reload | As expected | Pass |
| TC24 | Task Management | Worker attempts to update another worker's task | Forged POST with different task_id | Error: "You are not authorized to update this task." | As expected | Pass |
| TC25 | Inventory Management | Add item below minimum stock | Quantity < minimum_stock_level | Item flagged with "Low Stock" badge | As expected | Pass |
| TC26 | Inventory Management | Add item with negative cost | Cost = -100 | Error: "Cost cannot be negative." | As expected | Pass |
| TC27 | Expense Management | Add expense with valid data | Category, positive amount, valid date | Expense recorded, total updated | As expected | Pass |
| TC28 | Expense Management | Add expense with zero amount | Amount = 0 | Error: "Amount must be a positive number." | As expected | Pass |
| TC29 | Dashboard | Admin views dashboard | Login as admin | Stats and 4 charts render correctly | As expected | Pass |
| TC30 | Dashboard | Worker views dashboard | Login as worker | Only assigned-task stats shown, no admin charts | As expected | Pass |
| TC31 | Reports | View reports page as admin | Navigate to `/reports` | Summarized totals and breakdowns displayed | As expected | Pass |
| TC32 | Error Handling | Navigate to invalid URL | e.g. `/nonexistent-page` | Custom 404 page displayed | As expected | Pass |
| TC33 | Security | Attempt SQL injection in search box | `' OR '1'='1` in search field | Query safely parameterized, no data leak | As expected | Pass |
| TC34 | Security | Verify passwords are hashed | Inspect `users` table | `password_hash` column contains hashed value, not plain text | As expected | Pass |

## Summary
- **Total Test Cases:** 34
- **Passed:** 34
- **Failed:** 0
- All positive and negative test cases behaved as expected after fixes were applied
  during development (see Phase 5 for implementation notes).
