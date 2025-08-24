# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='home'),
    path('api/sales-data/', views.sales_chart_data, name='sales_chart_data'),
    path('api/inventory-alerts/', views.inventory_alerts_data, name='inventory_alerts_data'),
]