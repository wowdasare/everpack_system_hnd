# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales
    path('', views.SaleListView.as_view(), name='sale_list'),
    path('new/', views.SaleCreateView.as_view(), name='sale_create'),
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale_detail'),
    path('<int:pk>/edit/', views.SaleUpdateView.as_view(), name='sale_edit'),
    path('<int:sale_pk>/items/add/', views.SaleItemCreateView.as_view(), name='sale_item_add'),
    path('<int:pk>/invoice/', views.invoice_pdf, name='invoice_pdf'),
    path('<int:pk>/receipt/', views.receipt_pdf, name='receipt_pdf'),

    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),

    # Payments
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('sales/<int:sale_id>/payments/add/', views.PaymentCreateView.as_view(), name='payment_add'),

    # Bulk Orders
    path('bulk-orders/', views.BulkOrderListView.as_view(), name='bulk_order_list'),
    path('bulk-orders/add/', views.BulkOrderCreateView.as_view(), name='bulk_order_add'),
    path('bulk-orders/<int:pk>/', views.BulkOrderDetailView.as_view(), name='bulk_order_detail'),
    path('bulk-orders/<int:pk>/edit/', views.BulkOrderUpdateView.as_view(), name='bulk_order_edit'),
    path('bulk-orders/<int:pk>/convert/', views.convert_bulk_order_to_sale, name='convert_bulk_order'),
    path('bulk-orders/<int:pk>/receipt/', views.bulk_order_receipt_pdf, name='bulk_order_receipt_pdf'),

    # API endpoints for AJAX
    path('api/product-price/', views.get_product_price, name='get_product_price'),
    path('api/customer-search/', views.customer_search, name='customer_search'),
]