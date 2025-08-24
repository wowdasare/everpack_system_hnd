# reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportsHomeView.as_view(), name='home'),
    path('sales/', views.SalesReportView.as_view(), name='sales_report'),
    path('inventory/', views.InventoryReportView.as_view(), name='inventory_report'),
    path('financial/', views.FinancialReportView.as_view(), name='financial_report'),
    path('customer/', views.CustomerReportView.as_view(), name='customer_report'),
    path('profit-loss/', views.ProfitLossReportView.as_view(), name='profit_loss_report'),

    # Export endpoints
    path('sales/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('sales/export/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('inventory/export/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
    path('inventory/export/excel/', views.export_inventory_excel, name='export_inventory_excel'),
]