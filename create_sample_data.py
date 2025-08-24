#!/usr/bin/env python
"""
Script to create sample data for EverPack System
Run with: python manage.py shell < create_sample_data.py
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Add the project directory to the path
sys.path.append('/Users/mac/PycharmProjects/everpack_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'everpack_system.settings')
django.setup()

from django.contrib.auth.models import User
from inventory.models import Category, Supplier, Product, StockMovement
from sales.models import Customer, Sale, SaleItem

def create_sample_data():
    print("Creating sample data...")
    
    # Create categories
    categories = [
        {'name': 'Toilet Paper', 'description': 'Various types of toilet paper'},
        {'name': 'Facial Tissue', 'description': 'Facial tissues and napkins'},
        {'name': 'Paper Towels', 'description': 'Kitchen and cleaning paper towels'},
        {'name': 'Industrial Paper', 'description': 'Industrial grade paper products'},
    ]
    
    category_objects = []
    for cat_data in categories:
        category, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        category_objects.append(category)
        print(f"{'Created' if created else 'Found'} category: {category.name}")
    
    # Create suppliers
    suppliers_data = [
        {
            'name': 'Paper Mills Ghana Ltd',
            'contact_person': 'John Mensah',
            'phone': '+233-24-123-4567',
            'email': 'john@papermills.gh',
            'address': 'Industrial Area, Tema, Ghana'
        },
        {
            'name': 'Tissue World Suppliers',
            'contact_person': 'Mary Asante',
            'phone': '+233-20-987-6543',
            'email': 'mary@tissueworld.com',
            'address': 'Spintex Road, Accra, Ghana'
        },
        {
            'name': 'Global Paper Co.',
            'contact_person': 'Samuel Osei',
            'phone': '+233-54-555-1234',
            'email': 'samuel@globalpaper.gh',
            'address': 'Kumasi, Ashanti Region, Ghana'
        }
    ]
    
    supplier_objects = []
    for sup_data in suppliers_data:
        supplier, created = Supplier.objects.get_or_create(
            name=sup_data['name'],
            defaults=sup_data
        )
        supplier_objects.append(supplier)
        print(f"{'Created' if created else 'Found'} supplier: {supplier.name}")
    
    # Create products
    products_data = [
        {
            'name': 'Premium Toilet Paper 2-Ply (24 Roll Pack)',
            'description': 'Soft 2-ply toilet paper, 24 rolls per pack',
            'category': category_objects[0],
            'sku': 'TP-PREM-24',
            'unit': 'PACK',
            'cost_price': Decimal('15.50'),
            'selling_price': Decimal('22.00'),
            'minimum_stock_level': 20,
            'supplier': supplier_objects[0],
        },
        {
            'name': 'Economy Toilet Paper 1-Ply (36 Roll Pack)',
            'description': 'Budget-friendly 1-ply toilet paper, 36 rolls per pack',
            'category': category_objects[0],
            'sku': 'TP-ECO-36',
            'unit': 'PACK',
            'cost_price': Decimal('12.00'),
            'selling_price': Decimal('18.50'),
            'minimum_stock_level': 30,
            'supplier': supplier_objects[0],
        },
        {
            'name': 'Facial Tissue Box (200 Sheets)',
            'description': '3-ply facial tissue, 200 sheets per box',
            'category': category_objects[1],
            'sku': 'FT-BOX-200',
            'unit': 'PIECE',
            'cost_price': Decimal('3.50'),
            'selling_price': Decimal('5.50'),
            'minimum_stock_level': 50,
            'supplier': supplier_objects[1],
        },
        {
            'name': 'Kitchen Paper Towel (2 Roll Pack)',
            'description': 'Absorbent kitchen paper towels, 2 rolls per pack',
            'category': category_objects[2],
            'sku': 'KPT-2ROLL',
            'unit': 'PACK',
            'cost_price': Decimal('8.00'),
            'selling_price': Decimal('12.50'),
            'minimum_stock_level': 25,
            'supplier': supplier_objects[1],
        },
        {
            'name': 'Industrial Paper Towel (12 Roll Carton)',
            'description': 'Heavy-duty industrial paper towels, 12 rolls per carton',
            'category': category_objects[3],
            'sku': 'IPT-12ROLL',
            'unit': 'CARTON',
            'cost_price': Decimal('35.00'),
            'selling_price': Decimal('52.00'),
            'minimum_stock_level': 15,
            'supplier': supplier_objects[2],
        }
    ]
    
    product_objects = []
    admin_user = User.objects.get(username='admin')
    
    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            sku=prod_data['sku'],
            defaults=prod_data
        )
        product_objects.append(product)
        print(f"{'Created' if created else 'Found'} product: {product.name}")
        
        # Create initial stock movement
        if created:
            initial_stock = StockMovement.objects.create(
                product=product,
                movement_type='IN',
                quantity=100,  # Starting with 100 units
                reason='PURCHASE',
                reference_number='INITIAL-001',
                notes='Initial stock',
                created_by=admin_user
            )
            print(f"  Added initial stock: {initial_stock.quantity} units")
    
    # Create customers
    customers_data = [
        {
            'name': 'Accra Supermarket Ltd',
            'customer_type': 'WHOLESALE',
            'phone': '+233-30-277-4455',
            'email': 'orders@accrasupermarket.gh',
            'address': 'Osu, Accra, Ghana',
            'credit_limit': Decimal('5000.00'),
        },
        {
            'name': 'Corner Shop Enterprise',
            'customer_type': 'RETAIL',
            'phone': '+233-24-888-9999',
            'address': 'Dansoman, Accra, Ghana',
            'credit_limit': Decimal('1000.00'),
        },
        {
            'name': 'Hotel Golden Tulip',
            'customer_type': 'WHOLESALE',
            'phone': '+233-30-201-4000',
            'email': 'procurement@goldentulip.gh',
            'address': 'Airport Residential Area, Accra, Ghana',
            'tin_number': 'TIN-123456789',
            'credit_limit': Decimal('10000.00'),
        },
        {
            'name': 'Regional Distributor GH',
            'customer_type': 'DISTRIBUTOR',
            'phone': '+233-50-123-7890',
            'email': 'sales@regionaldist.gh',
            'address': 'Kumasi, Ashanti Region, Ghana',
            'tin_number': 'TIN-987654321',
            'credit_limit': Decimal('25000.00'),
        }
    ]
    
    customer_objects = []
    for cust_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            name=cust_data['name'],
            defaults=cust_data
        )
        customer_objects.append(customer)
        print(f"{'Created' if created else 'Found'} customer: {customer.name}")
    
    # Create sample sales
    print("Creating sample sales...")
    for i in range(5):
        sale = Sale.objects.create(
            customer=customer_objects[i % len(customer_objects)],
            payment_method='CASH' if i % 2 == 0 else 'MOBILE_MONEY',
            payment_status='PAID',
            created_by=admin_user,
        )
        
        # Add sale items
        num_items = min(2 + i, len(product_objects))
        for j in range(num_items):
            product = product_objects[j]
            quantity = 2 + (i * j)
            if quantity > 0:
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=product.selling_price,
                    total_price=quantity * product.selling_price
                )
                
                # Create stock movement for sale
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                    reason='SALE',
                    reference_number=sale.invoice_number,
                    created_by=admin_user
                )
        
        # Calculate sale totals
        sale.calculate_totals()
        sale.amount_paid = sale.total_amount
        sale.save()
        
        print(f"Created sale {sale.invoice_number} for {sale.customer.name} - GHS {sale.total_amount}")
    
    print("\nSample data creation completed!")
    print("You can now log in with:")
    print("Username: admin")
    print("Password: admin123")
    print("Server running at: http://127.0.0.1:8000")

if __name__ == '__main__':
    create_sample_data()