# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EverPack System is a Django 5.2.4 web application for inventory and sales management. It's designed for packaging/wholesale businesses with features for tracking inventory, managing sales, and generating reports.

## Development Commands

### Running the Application
```bash
python manage.py runserver
```

### Database Operations
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Testing
```bash
python manage.py test
```

## Application Architecture

### Core Apps Structure
The system is organized into 5 main Django apps:

- **dashboard**: Main landing page and overview dashboard
- **inventory**: Product catalog, supplier management, and stock tracking
- **sales**: Customer management, sales processing, and payment handling
- **reports**: Analytics and reporting functionality
- **accounts**: User authentication and account management (basic Django auth)

### Key Models and Relationships

**Inventory App (`inventory/models.py`)**:
- `Product` - Core product catalog with SKU, pricing, stock levels
- `Category` - Product categorization
- `Supplier` - Vendor/supplier information
- `StockMovement` - All inventory transactions (IN/OUT/ADJUSTMENT)
- `StockAlert` - Low stock and overstock notifications

**Sales App (`sales/models.py`)**:
- `Customer` - Customer database with types (retail/wholesale/distributor)
- `Sale` - Sales transactions with auto-generated invoice numbers
- `SaleItem` - Line items within sales
- `Payment` - Payment tracking for credit sales
- `SalesTarget` - Performance targets and tracking

### URL Structure
- Root (`/`) redirects to dashboard
- `/admin/` - Django admin interface
- `/dashboard/` - Main dashboard and overview
- `/inventory/` - Product and stock management
- `/sales/` - Sales processing and customer management
- `/reports/` - Analytics and reporting
- `/accounts/` - Authentication and user management

### Database Configuration
- Uses SQLite3 for development (`db.sqlite3`)
- Database path: `BASE_DIR / 'db.sqlite3'`

### Key Business Logic

**Stock Tracking**: 
- Stock levels calculated via `StockMovement` records
- Products have `current_stock` property that sums IN/OUT movements
- Automatic low stock detection via `is_low_stock` property

**Sales Processing**:
- Auto-generated invoice numbers (format: `INV-000001`)
- Supports multiple payment methods and statuses
- Profit margin calculations at product and sale level
- Customer credit limit and outstanding balance tracking

**Templates**: 
- Template directory configured at `BASE_DIR / 'templates'`
- Uses standard Django template structure

When working with this codebase, focus on maintaining the existing model relationships and business logic patterns, especially around stock movement tracking and sales processing workflows.