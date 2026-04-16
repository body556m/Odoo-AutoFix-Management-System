# AutoFix - Car Workshop Management System

A comprehensive Odoo 17 module for managing car workshop operations, including vehicle registration, service reception, work orders, appointments, inspections, and warranty tracking.

## Features

### Vehicle Management
- **Car Registration**: Register vehicles with brand, model, year, VIN, mileage, fuel type, transmission, insurance information
- **Car Brands & Models**: Master data for car brands and models
- **Service History**: Track all service receptions per vehicle

### Service Reception
- **Service Orders**: Create and manage service receptions with customer complaints
- **Service Types**: Predefined service categories (Mechanical, Electrical, Body Work, Paint, A/C, Tires, General)
- **Priority Levels**: Normal, Low, High, Urgent
- **Workflow**: Draft → In Progress → Done → Cancelled

### Work Orders
- **Work Order Management**: Assign mechanics to specific tasks
- **Parts Tracking**: Track parts used with stock integration
- **Expense Tracking**: Track additional expenses per work order
- **Quality Control**: Quality check fields for mechanic confirmation
- **Time Tracking**: Start/end time tracking, duration calculation

### Appointments
- **Customer Appointments**: Schedule customer visits with date/time slots
- **Calendar View**: Visual calendar for appointment management
- **Auto-Reception**: Create service reception from appointment arrival

### Vehicle Inspections
- **Inspection Templates**: Create reusable checklist templates
- **Inspection Reports**: Record detailed inspection results with conditions
- **Categories**: Engine, Brakes, Suspension, Electrical, Body, Tires, Fluids, Interior, Exterior

### Warranty Tracking
- **Warranty Records**: Track warranty for parts/labor/full
- **Warranty Claims**: Manage warranty claims with approval workflow
- **Auto-Expiry**: Cron job to automatically mark expired warranties

### Customer Feedback
- **Ratings**: 1-5 star rating system
- **Service Quality**: Track service quality, cleanliness, timeliness
- **Recommendations**: Track if customer would recommend

### Financial
- **Petty Cash**: Expense tracking with approval workflow
- **Payroll**: Employee wage management and payroll runs
- **Invoicing**: Generate invoices from service receptions
- **Inventory Audit**: Stock inventory verification

## Module Dependencies

- `base`
- `mail`
- `hr`
- `account`
- `stock`
- `purchase`

## Security Groups

| Group | Description |
|-------|-------------|
| AutoFix / Manager | Full access to all features |
| AutoFix / Accountant | Access to petty cash and payroll |
| AutoFix / Receptionist | Manage receptions, appointments |
| AutoFix / Mechanic | Manage own work orders |

## API Endpoints

The module provides REST API endpoints for external integrations:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/autofix/receptions` | GET | List service receptions |
| `/api/autofix/receptions/<id>` | GET | Get single reception |
| `/api/autofix/work-orders` | GET | List work orders |
| `/api/autofix/cars` | GET | List registered cars |
| `/api/autofix/dashboard` | GET | Get dashboard KPIs |

## Module Structure

```
autofix/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py           # REST API controllers
├── data/
│   ├── sequence.xml      # Sequences
│   ├── cron.xml          # Scheduled actions
│   ├── record_rules.xml  # Access rules
│   └── ...
├── models/
│   ├── __init__.py
│   ├── car.py            # Vehicle model
│   ├── car_brand.py      # Brand/model master data
│   ├── service_type.py   # Service categories
│   ├── service_reception.py
│   ├── work_order.py
│   ├── petty_cash.py
│   ├── vehicle_inspection.py
│   ├── warranty.py
│   ├── appointment.py
│   ├── customer_feedback.py
│   └── ...
├── report/
│   └── ...
├── security/
│   ├── groups.xml        # Security groups
│   └── ir.model.access.csv
├── views/
│   ├── menus.xml
│   ├── car_views.xml
│   └── ...
├── wizard/
│   └── ...
└── static/
    ├── src/
    │   ├── css/dashboard.css
    │   ├── js/dashboard.js
    │   └── xml/dashboard.xml
    └── description/
        └── icon.png
```

## Version History

- **17.0.0.2.0**: Added vehicle inspections, warranties, appointments, customer feedback, REST API, enhanced security
- **17.0.0.1.0**: Initial release with core features

## License

Proprietary - All rights reserved

## Author

Abdo Mohamed