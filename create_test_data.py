#!/usr/bin/env python
import os
import sys
import django

# Set up Django
sys.path.append('/Users/mac/PycharmProjects/everpack_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'everpack_system.settings')
django.setup()

from sales.models import Customer
from inventory.models import Category, Supplier, Product
from django.contrib.auth.models import User

def create_test_data():
    print("Creating test data...")
    
    # Create a test user if needed
    if not User.objects.filter(username='testuser').exists():
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        print("✓ Created test user")
    
    # Create categories
    if not Category.objects.exists():
        categories = [
            {'name': 'Packaging Materials', 'description': 'Various packaging materials'},
            {'name': 'Containers', 'description': 'Storage and shipping containers'},
            {'name': 'Labels & Stickers', 'description': 'Labels and adhesive materials'},
        ]
        for cat_data in categories:
            Category.objects.create(**cat_data)
        print("✓ Created categories")
    
    # Create suppliers
    if not Supplier.objects.exists():
        suppliers = [
            {
                'name': 'PackCorp Ltd',
                'contact_person': 'John Smith',
                'phone': '+233-123-456-789',
                'email': 'contact@packcorp.com',
                'address': '123 Industrial Area, Accra'
            },
            {
                'name': 'Ghana Packaging Co',
                'contact_person': 'Mary Asante',
                'phone': '+233-987-654-321', 
                'email': 'info@ghanapack.com',
                'address': '456 Trade Zone, Tema'
            }
        ]
        for supplier_data in suppliers:
            Supplier.objects.create(**supplier_data)
        print("✓ Created suppliers")
    
    # Create products
    if not Product.objects.exists():
        category = Category.objects.first()
        supplier = Supplier.objects.first()
        
        products = [
            {
                'name': 'Cardboard Box - Medium',
                'description': 'Medium sized cardboard shipping box',
                'category': category,
                'sku': 'BOX-MED-001',
                'unit': 'PIECE',
                'cost_price': 2.50,
                'selling_price': 4.00,
                'minimum_stock_level': 50,
                'supplier': supplier
            },
            {
                'name': 'Plastic Container - 1L',
                'description': '1 liter plastic storage container',
                'category': category,
                'sku': 'CONT-1L-001',
                'unit': 'PIECE',
                'cost_price': 1.20,
                'selling_price': 2.00,
                'minimum_stock_level': 100,
                'supplier': supplier
            },
            {
                'name': 'Packaging Tape Roll',
                'description': 'Clear adhesive packaging tape',
                'category': category,
                'sku': 'TAPE-CLEAR-001',
                'unit': 'ROLL',
                'cost_price': 3.00,
                'selling_price': 5.00,
                'minimum_stock_level': 25,
                'supplier': supplier
            }
        ]
        
        for product_data in products:
            Product.objects.create(**product_data)
        print("✓ Created products")
    
    # Create customers
    if not Customer.objects.exists():
        customers = [
            {
                'name': 'ABC Trading Company',
                'customer_type': 'WHOLESALE',
                'phone': '+233-111-222-333',
                'email': 'orders@abctrading.com',
                'address': '789 Commercial Street, Accra',
                'credit_limit': 10000.00
            },
            {
                'name': 'John Doe',
                'customer_type': 'RETAIL',
                'phone': '+233-444-555-666',
                'email': 'john.doe@email.com',
                'address': '321 Residential Area, Kumasi',
                'credit_limit': 1000.00
            },
            {
                'name': 'XYZ Distributors',
                'customer_type': 'DISTRIBUTOR',
                'phone': '+233-777-888-999',
                'email': 'sales@xyzdist.com',
                'address': '654 Industrial Zone, Takoradi',
                'credit_limit': 50000.00
            }
        ]
        
        for customer_data in customers:
            Customer.objects.create(**customer_data)
        print("✓ Created customers")
    
    # Add some initial stock for products
    from inventory.models import StockMovement
    
    if not StockMovement.objects.exists():
        user = User.objects.first()
        for product in Product.objects.all():
            StockMovement.objects.create(
                product=product,
                movement_type='IN',
                quantity=200,  # Add initial stock
                reason='PURCHASE',
                reference_number='INIT-001',
                notes='Initial stock',
                created_by=user
            )
        print("✓ Added initial stock")
    
    print("Test data creation completed!")

if __name__ == '__main__':
    create_test_data()