# sales/models.py
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
import uuid
from inventory.models import Product


class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('RETAIL', 'Retail Customer'),
        ('WHOLESALE', 'Wholesale Customer'),
        ('DISTRIBUTOR', 'Distributor'),
    ]

    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=12, choices=CUSTOMER_TYPES, default='RETAIL')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    tin_number = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        """Calculate total outstanding balance"""
        return self.sales.filter(payment_status='PENDING').aggregate(
            total=models.Sum('total_amount'))['total'] or 0

    @property
    def total_purchases(self):
        """Calculate total purchases made by customer"""
        return self.sales.aggregate(
            total=models.Sum('total_amount'))['total'] or 0

    class Meta:
        ordering = ['name']


class Sale(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
        ('OVERDUE', 'Overdue'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('CREDIT', 'Credit'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PAID')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            last_sale = Sale.objects.order_by('-id').first()
            if last_sale:
                last_number = int(last_sale.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.invoice_number = f"INV-{new_number:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"

    def get_absolute_url(self):
        return reverse('sales:sale_detail', kwargs={'pk': self.pk})

    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return self.total_amount - self.amount_paid

    @property
    def total_items(self):
        """Calculate total number of items in sale"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def total_profit(self):
        """Calculate total profit from sale"""
        total_profit = 0
        for item in self.items.all():
            item_profit = (item.unit_price - item.product.cost_price) * item.quantity
            total_profit += item_profit
        return total_profit

    def calculate_totals(self):
        """Calculate and update sale totals"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        self.save()

    class Meta:
        ordering = ['-created_at']


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def profit(self):
        """Calculate profit for this item"""
        return (self.unit_price - self.product.cost_price) * self.quantity

    class Meta:
        unique_together = ['sale', 'product']


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.sale.invoice_number}"

    class Meta:
        ordering = ['-created_at']


class SalesTarget(models.Model):
    PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_targets')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.period} Target - GHS {self.target_amount}"

    @property
    def achieved_amount(self):
        """Calculate achieved sales amount for the target period"""
        return Sale.objects.filter(
            created_by=self.assigned_to,
            sale_date__range=[self.start_date, self.end_date],
            payment_status='PAID'
        ).aggregate(total=models.Sum('total_amount'))['total'] or 0

    @property
    def achievement_percentage(self):
        """Calculate achievement percentage"""
        if self.target_amount > 0:
            return (self.achieved_amount / self.target_amount) * 100
        return 0

    class Meta:
        ordering = ['-created_at']