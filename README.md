# AutoFix - Odoo 17 Auto Repair Management Module

## Overview
AutoFix is a comprehensive, custom-built Odoo 17 module designed specifically for Auto Repair Shops and Garages. It streamlines daily operations by managing cars, service receptions, work orders, inventory, expenses, and employee payroll within a unified system. It is heavily integrated with Odoo's standard applications such as Contacts, Mail, HR, Accounting, Stock, and Purchase.

## Features

### 1. Core Operations
*   **Car Management:** Register and track vehicles with details like brand, model, year, VIN/Chassis, and initial mileage.
*   **Service Receptions:** Manage customer visits from entry to exit. Tracks car status, customer complaints, and generates automated sequences.
*   **Work Orders:** Assign specific repair jobs to mechanics (HR Employees). Track state (Pending, In Progress, Done, Cancelled), labor costs, used spare parts, and external expenses.
*   **Petty Cash Management:** Simple tracking for daily shop expenses and small outlays by managers.

### 2. ERP Integration
*   **Accounting (Invoicing):** Seamlessly converts Service Receptions into `account.move` invoices containing labor, parts, and additional expenses. Includes automated warning and cancellation functions for unpaid invoices.
*   **Inventory (Stock):** Tracks consumed spare parts in work orders, creating direct stock moves. Integrates with the purchase module for automatic reordering when stock drops below minimum quantities.
*   **Human Resources (Payroll):** Calculates mechanics' monthly wages based on base salary and performance bonuses per completed work order.
*   **Mail & Communications:** Automatically sends a daily summary email to managers including work order statistics, financial summaries, mechanics' performance, and stock alerts.

### 3. Advanced Features
*   **Management Dashboard (OWL):** A dynamic, reactive dashboard built with Odoo's OWL framework. It displays key performance indicators (KPIs), open work orders, mechanic performance, and immediate financial summaries.
*   **Automated Actions (Cron Jobs):**
    *   Daily Manager Summary Report.
    *   15-day reminder for unpaid invoices.
    *   30-day automatic cancellation of overdue unpaid invoices.
*   **Reporting (QWeb PDF):**
    *   Comprehensive Maintenance Invoices.
    *   Inventory Audit Reports.
    *   Mechanics Payroll Reports.
*   **Auditing Tools:** Dedicated wizard for Monthly/Annual inventory checks, resulting in a printable financial and stock summary.

## Architecture & Data Models
The application relies on several interconnected models:
*   `autofix.car`: Central record for vehicles.
*   `autofix.service.reception`: Parent record for a service visit. Relates `1:M` with work orders.
*   `autofix.work.order`: Granular repair tasks related to the reception.
*   `autofix.work.order.part`: Lines for parts consumed (`M:1` to work order).
*   `autofix.work.order.expense`: Lines for external expenses (`M:1` to work order).
*   `autofix.petty.cash`: Independent records for shop expenses.
*   `autofix.inventory.audit` & `autofix.inventory.audit.line`: Wizards and lines for stock checking.
*   `autofix.payroll` & `autofix.payroll.line`: Wizards for generating mechanic salaries.

## Technologies Used
*   **Framework:** Odoo 17 ORM
*   **Backend:** Python 3
*   **Frontend (Views & Reports):** XML, QWeb templating
*   **Frontend (Dashboard):** OWL (Odoo Web Library) / JavaScript / CSS
*   **Database:** PostgreSQL

## Access Rights & Security
AutoFix provides role-based access control with three main groups:
*   **AutoFix / Manager:** Full access to all features, settings, financial data, payroll, and the management dashboard.
*   **AutoFix / Receptionist:** Access to create and manage cars, service receptions, and create basic work orders.
*   **AutoFix / Mechanic:** Limited access to view assigned work orders and update their statuses to complete the jobs.
