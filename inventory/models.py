# inventory/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'


class Product(models.Model):
    UNIT_CHOICES = [
        ('PACK', 'Pack'),
        ('CARTON', 'Carton'),
        ('PIECE', 'Piece'),
        ('ROLL', 'Roll'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='PACK')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_stock_level = models.PositiveIntegerField(default=10)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def get_absolute_url(self):
        return reverse('inventory:product_detail', kwargs={'pk': self.pk})

    @property
    def current_stock(self):
        """Calculate current stock level"""
        stock_in = self.stock_movements.filter(movement_type='IN').aggregate(
            total=models.Sum('quantity'))['total'] or 0
        stock_out = self.stock_movements.filter(movement_type='OUT').aggregate(
            total=models.Sum('quantity'))['total'] or 0
        return stock_in - stock_out

    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.cost_price

    @property
    def is_low_stock(self):
        """Check if stock is below minimum level"""
        return self.current_stock <= self.minimum_stock_level

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0

    class Meta:
        ordering = ['name']


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
    ]

    MOVEMENT_REASONS = [
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('RETURN', 'Return'),
        ('DAMAGE', 'Damage'),
        ('THEFT', 'Theft'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('TRANSFER', 'Transfer'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=MOVEMENT_REASONS)
    reference_number = models.CharField(max_length=100, blank=True, help_text="Invoice/Receipt number")
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} - {self.quantity}"

    class Meta:
        ordering = ['-created_at']


class StockAlert(models.Model):
    ALERT_TYPES = [
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('OVERSTOCK', 'Overstock'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} - {self.alert_type}"

    class Meta:
        ordering = ['-created_at']