from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from .models import Product, Supplier, Category, StockMovement, StockAlert


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate stock percentage vs minimum level
        if self.object.minimum_stock_level > 0:
            stock_percentage = (self.object.current_stock / self.object.minimum_stock_level) * 100
            context['stock_percentage'] = min(100, stock_percentage)  # Cap at 100% for display
        else:
            context['stock_percentage'] = 100 if self.object.current_stock > 0 else 0
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    template_name = 'inventory/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'barcode', 'unit', 'cost_price', 'selling_price', 'minimum_stock_level', 'supplier', 'is_active']
    
    def form_valid(self, form):
        messages.success(self.request, f'Product "{form.instance.name}" has been created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    template_name = 'inventory/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'barcode', 'unit', 'cost_price', 'selling_price', 'minimum_stock_level', 'supplier', 'is_active']
    
    def form_valid(self, form):
        messages.success(self.request, f'Product "{form.instance.name}" has been updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'inventory/supplier_detail.html'
    context_object_name = 'supplier'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_products_count'] = self.object.products.filter(is_active=True).count()
        return context


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    template_name = 'inventory/supplier_form.html'
    fields = '__all__'


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    template_name = 'inventory/supplier_form.html'
    fields = '__all__'


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'inventory/supplier_confirm_delete.html'
    success_url = reverse_lazy('inventory:supplier_list')


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    template_name = 'inventory/category_form.html'
    fields = '__all__'


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    template_name = 'inventory/category_form.html'
    fields = '__all__'


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')


class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/stock_movement_list.html'
    context_object_name = 'movements'


class StockMovementCreateView(LoginRequiredMixin, CreateView):
    model = StockMovement
    template_name = 'inventory/stock_movement_form.html'
    fields = ['product', 'movement_type', 'quantity', 'reason', 'reference_number', 'notes']
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Stock movement for "{form.instance.product.name}" has been recorded!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:stock_movement_list')


class LowStockView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/low_stock.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['low_stock_products'] = Product.objects.filter(
            id__in=[p.id for p in Product.objects.all() if p.is_low_stock]
        )
        return context


class StockAlertListView(LoginRequiredMixin, ListView):
    model = StockAlert
    template_name = 'inventory/stock_alert_list.html'
    context_object_name = 'alerts'
