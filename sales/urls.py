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

    # API endpoints for AJAX
    path('api/product-price/', views.get_product_price, name='get_product_price'),
    path('api/customer-search/', views.customer_search, name='customer_search'),
]