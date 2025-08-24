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
        
        # Today's sales
        today_sales = Sale.objects.filter(
            sale_date__date=today,
            payment_status='PAID'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        context['today_sales'] = f"GHS {today_sales:.2f}"
        
        # Low stock count
        low_stock_products = [p for p in Product.objects.all() if p.is_low_stock]
        context['low_stock_count'] = len(low_stock_products)
        
        # Total customers
        context['total_customers'] = Customer.objects.filter(is_active=True).count()
        
        # Recent sales
        context['recent_sales'] = Sale.objects.select_related('customer').order_by('-created_at')[:5]
        
        return context


def sales_chart_data(request):
    # Get last 7 days of sales data
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    sales_data = []
    labels = []
    
    for i in range(7):
        date = week_ago + timedelta(days=i)
        day_sales = Sale.objects.filter(
            sale_date__date=date,
            payment_status='PAID'
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
