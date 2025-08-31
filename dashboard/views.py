from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from inventory.models import Product, StockAlert
from sales.models import Sale, Customer


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Dashboard'
        
        # Get dashboard statistics
        today = timezone.now().date()
        
        # Total products
        context['total_products'] = Product.objects.filter(is_active=True).count()
        
        # Today's sales (all sales regardless of payment status)
        today_sales = Sale.objects.filter(
            sale_date__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        context['today_sales'] = f"GHS {today_sales:.2f}"
        
        # Low stock count
        low_stock_products = [p for p in Product.objects.all() if p.is_low_stock]
        context['low_stock_count'] = len(low_stock_products)
        
        # Total customers
        context['total_customers'] = Customer.objects.filter(is_active=True).count()
        
        # Recent sales
        context['recent_sales'] = Sale.objects.select_related('customer').order_by('-created_at')[:5]
        
        # Recent activities (combination of different activities)
        recent_activities = []
        
        # Recent sales
        recent_sales = Sale.objects.select_related('customer').order_by('-created_at')[:3]
        for sale in recent_sales:
            recent_activities.append({
                'type': 'sale',
                'icon': 'bi-cart-check',
                'title': f'Sale Created: {sale.invoice_number}',
                'description': f'Customer: {sale.customer.name} • Amount: GHS {sale.total_amount}',
                'timestamp': sale.created_at,
                'color': 'success' if sale.payment_status == 'PAID' else 'warning'
            })
        
        # Recent user registrations (if admin)
        if self.request.user.is_staff:
            from django.contrib.auth.models import User
            recent_users = User.objects.exclude(id=self.request.user.id).order_by('-date_joined')[:2]
            for user in recent_users:
                recent_activities.append({
                    'type': 'user',
                    'icon': 'bi-person-plus',
                    'title': f'New User: {user.get_full_name() or user.username}',
                    'description': f'Account created • Role: {user.groups.first().name if user.groups.exists() else "No role"}',
                    'timestamp': user.date_joined,
                    'color': 'info'
                })
        
        # Recent stock movements (only for users who can access stock movements)
        user_role = None
        if self.request.user.groups.exists():
            user_role = self.request.user.groups.first().name
        elif self.request.user.is_superuser:
            user_role = 'admin'
        
        # Only show stock movements to admin and manager roles, not sales_rep
        if user_role in ['admin', 'manager']:
            from inventory.models import StockMovement
            recent_stock_moves = StockMovement.objects.select_related('product').order_by('-created_at')[:2]
            for movement in recent_stock_moves:
                recent_activities.append({
                    'type': 'stock',
                    'icon': 'bi-arrow-up' if movement.movement_type == 'IN' else 'bi-arrow-down',
                    'title': f'Stock {movement.get_movement_type_display()}',
                    'description': f'{movement.product.name} • Quantity: {movement.quantity} • {movement.reference_number or movement.reason}',
                    'timestamp': movement.created_at,
                    'color': 'primary' if movement.movement_type == 'IN' else 'secondary'
                })
        
        # Recent customers (for all roles)
        recent_customers = Customer.objects.order_by('-created_at')[:2]
        for customer in recent_customers:
            recent_activities.append({
                'type': 'customer',
                'icon': 'bi-person-plus-fill',
                'title': f'New Customer: {customer.name}',
                'description': f'Type: {customer.get_customer_type_display()} • Phone: {customer.phone or "N/A"}',
                'timestamp': customer.created_at,
                'color': 'info'
            })
        
        # Recent bulk orders (for sales roles)
        if user_role in ['admin', 'manager', 'sales_rep']:
            from sales.models import BulkOrder
            recent_bulk_orders = BulkOrder.objects.select_related('customer').order_by('-created_at')[:2]
            for bulk_order in recent_bulk_orders:
                recent_activities.append({
                    'type': 'bulk_order',
                    'icon': 'bi-boxes',
                    'title': f'Bulk Order: {bulk_order.bulk_order_number}',
                    'description': f'Customer: {bulk_order.customer.name} • Status: {bulk_order.get_status_display()}',
                    'timestamp': bulk_order.created_at,
                    'color': 'warning' if bulk_order.status == 'DRAFT' else 'success'
                })
        
        # Sort activities by timestamp (newest first)
        recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        context['recent_activities'] = recent_activities[:8]  # Show top 8 activities
        
        return context


def sales_chart_data(request):
    # Get last 7 days of sales data (including today)
    today = timezone.now().date()
    week_ago = today - timedelta(days=6)  # Changed from 7 to 6 to include today
    
    sales_data = []
    labels = []
    
    for i in range(7):
        date = week_ago + timedelta(days=i)
        # Show ALL sales (not just PAID) to match dashboard "Today's Sales"
        day_sales = Sale.objects.filter(
            sale_date__date=date
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        sales_data.append(float(day_sales))
        labels.append(date.strftime('%a'))
    
    return JsonResponse({
        'labels': labels,
        'data': sales_data
    })


def inventory_alerts_data(request):
    # Get low stock products
    low_stock_products = []
    for product in Product.objects.filter(is_active=True):
        if product.is_low_stock:
            low_stock_products.append({
                'name': product.name,
                'current_stock': product.current_stock,
                'minimum_level': product.minimum_stock_level,
                'sku': product.sku
            })
    
    return JsonResponse({
        'alerts': low_stock_products[:10]  # Limit to 10 alerts
    })
