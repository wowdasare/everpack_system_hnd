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

- **dashboard**: Main landing page and overview dashboard with role-based Recent Activities
- **inventory**: Product catalog, supplier management, and stock tracking
- **sales**: Customer management, sales processing, payment handling, and bulk orders
- **reports**: Analytics and reporting functionality (Sales Reports, Inventory Reports, P&L)
- **accounts**: User authentication, role-based access control, and account management

### Role-Based Access Control

The system implements comprehensive role-based permissions with three main user types:

**Administrator (`admin`)**:
- Full system access including user management
- Apps: Dashboard, Inventory, Sales, Reports, Accounts
- Actions: View, Add, Change, Delete
- Can manage stock movements and user accounts

**Manager (`manager`)**:
- Business operations access without user management
- Apps: Dashboard, Inventory, Sales, Reports  
- Actions: View, Add, Change (no delete)
- Can manage stock movements but not user accounts

**Sales Representative (`sales_rep`)**:
- Customer-facing operations focused on sales
- Apps: Dashboard, Inventory (limited), Sales
- Actions: View, Add, Change (no delete)
- Cannot access stock movements or detailed inventory management
- Sees simplified interfaces without stock management features

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
- `BulkOrder` - Multi-item orders for bulk clients with status workflow
- `BulkOrderItem` - Line items within bulk orders

**Accounts App (`accounts/models.py`, `accounts/middleware.py`)**:
- Uses Django's built-in User model with Groups for role assignment
- `RoleBasedAccessMiddleware` - Controls URL access by user role
- `role_tags.py` - Template tags for role-based UI rendering
- Custom user creation forms with role selection

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
- Stock levels calculated via `StockMovement` records with reference numbers
- Products have `current_stock` property that sums IN/OUT movements
- Automatic low stock detection via `is_low_stock` property
- Role-based access: Sales reps see stock levels but cannot modify them

**Sales Processing**:
- Auto-generated invoice numbers (format: `INV-000001`)
- Multiple payment statuses: PAID, PENDING, PARTIAL
- Today's Sales metric shows ALL sales (not just paid) for comprehensive business tracking
- Sales Overview chart displays last 7 days including today
- Profit margin calculations at product and sale level
- Customer credit limit and outstanding balance tracking

**Bulk Order Workflow**:
- Status progression: DRAFT → SUBMITTED → PROCESSING → COMPLETED
- Can be converted to regular sales transactions
- PDF generation for bulk order receipts

**Dashboard Features**:
- Role-based Recent Activities timeline (sales, users, stock movements, customers, bulk orders)
- Real-time metrics with consistent data across dashboard and charts
- Sales reps see activities relevant to their role (no stock movements)

**Permission System**:
- Middleware-enforced URL restrictions based on user roles
- Template-level UI filtering using custom role tags
- Navigation menus adapt to user permissions
- Consistent experience across all pages

**Templates**: 
- Template directory configured at `BASE_DIR / 'templates'`
- Uses standard Django template structure with role-based template tags
- Role permissions: `{% can_access_app user 'app_name' %}` and `{% can_perform_action user 'action' %}`

## Important Development Notes

When working with this codebase:

1. **Maintain Role Consistency**: Always use role-based template tags for UI elements
2. **Stock Movement Access**: Only admins/managers should see stock management features
3. **Sales Metrics**: Keep "Today's Sales" consistent between dashboard cards and charts (show ALL sales, not just PAID)
4. **Navigation**: Use middleware permissions to control both URL access and UI visibility
5. **User Creation**: Always assign users to appropriate groups for role-based access
6. **Template Changes**: Test with different user roles to ensure proper permission filtering

The system prioritizes role-based security and user experience consistency across all interfaces.