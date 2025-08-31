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
        from django.utils import timezone as django_timezone
        
        if not self.invoice_number:
            # Generate invoice number - only allow for current day
            today = django_timezone.now().date()
            
            # Get the latest invoice number for today
            today_sales = Sale.objects.filter(
                sale_date__date=today
            ).order_by('-id')
            
            if today_sales.exists():
                last_sale = today_sales.first()
                last_number = int(last_sale.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                # First sale of the day - start from where yesterday ended + 1
                last_sale = Sale.objects.order_by('-id').first()
                if last_sale:
                    last_number = int(last_sale.invoice_number.split('-')[-1])
                    new_number = last_number + 1
                else:
                    new_number = 1
            
            self.invoice_number = f"INV-{new_number:06d}"
            
        # Ensure sale date is today (prevent backdating invoices)
        if not self.pk:  # Only for new sales
            self.sale_date = django_timezone.now()
        
        # Update payment status based on amounts
        if self.total_amount > 0:
            if self.amount_paid >= self.total_amount:
                self.payment_status = 'PAID'
            elif self.amount_paid > 0:
                self.payment_status = 'PARTIAL'
            else:
                self.payment_status = 'PENDING'
        else:
            self.payment_status = 'PAID'  # Zero amount sales are considered paid
            
        super().save(*args, **kwargs)

    def clean(self):
        """Validate that sales can only be created for today"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone as django_timezone
        
        today = django_timezone.now().date()
        
        # For new sales, ensure they can only be created for today
        if not self.pk:  # New sale
            if self.sale_date:
                sale_date = self.sale_date.date() if hasattr(self.sale_date, 'date') else self.sale_date
                if sale_date != today:
                    raise ValidationError({
                        'sale_date': f'New invoices can only be created for today ({today.strftime("%Y-%m-%d")}). '
                                   f'Cannot create invoice for {sale_date.strftime("%Y-%m-%d")}.'
                    })
        else:  # Existing sale
            # Prevent editing of old sales (except for payments)
            existing_sale = Sale.objects.get(pk=self.pk)
            existing_date = existing_sale.sale_date.date()
            if existing_date != today:
                # Allow only payment-related updates on old sales
                if (self.amount_paid != existing_sale.amount_paid or 
                    self.payment_status != existing_sale.payment_status):
                    # Payment updates are allowed
                    pass
                else:
                    raise ValidationError({
                        '__all__': f'Cannot edit invoices from previous dates. '
                                 f'This invoice is from {existing_date.strftime("%Y-%m-%d")}. '
                                 f'Only payment updates are allowed on old invoices.'
                    })

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
        is_new = self.pk is None
        old_quantity = 0
        
        if not is_new:
            # Get the old quantity for stock adjustment
            old_item = SaleItem.objects.get(pk=self.pk)
            old_quantity = old_item.quantity
        
        super().save(*args, **kwargs)
        
        # Create stock movement for sale
        from inventory.models import StockMovement
        
        if is_new:
            # New item - create stock out movement
            StockMovement.objects.create(
                product=self.product,
                movement_type='OUT',
                quantity=self.quantity,
                reason='SALE',
                reference_number=self.sale.invoice_number,
                notes=f'Sale to {self.sale.customer.name}',
                created_by=self.sale.created_by
            )
        else:
            # Updated item - adjust stock
            quantity_diff = self.quantity - old_quantity
            if quantity_diff > 0:
                # Additional items sold
                StockMovement.objects.create(
                    product=self.product,
                    movement_type='OUT',
                    quantity=quantity_diff,
                    reason='SALE',
                    reference_number=self.sale.invoice_number,
                    notes=f'Sale adjustment to {self.sale.customer.name}',
                    created_by=self.sale.created_by
                )
            elif quantity_diff < 0:
                # Items returned/reduced
                StockMovement.objects.create(
                    product=self.product,
                    movement_type='IN',
                    quantity=abs(quantity_diff),
                    reason='RETURN',
                    reference_number=self.sale.invoice_number,
                    notes=f'Sale return from {self.sale.customer.name}',
                    created_by=self.sale.created_by
                )

    def delete(self, *args, **kwargs):
        # Return stock when item is deleted
        from inventory.models import StockMovement
        StockMovement.objects.create(
            product=self.product,
            movement_type='IN',
            quantity=self.quantity,
            reason='RETURN',
            reference_number=self.sale.invoice_number,
            notes=f'Sale item deleted - return to stock',
            created_by=self.sale.created_by
        )
        super().delete(*args, **kwargs)

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


class BulkOrder(models.Model):
    """Model for compiling multiple orders from different stock for a single client"""
    BULK_ORDER_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    bulk_order_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bulk_orders')
    status = models.CharField(max_length=12, choices=BULK_ORDER_STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bulk_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.bulk_order_number:
            # Generate bulk order number
            last_bulk_order = BulkOrder.objects.order_by('-id').first()
            if last_bulk_order:
                last_number = int(last_bulk_order.bulk_order_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.bulk_order_number = f"BULK-{new_number:06d}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.bulk_order_number} - {self.customer.name}"
    
    @property
    def total_items(self):
        """Calculate total number of items in bulk order"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def total_amount(self):
        """Calculate total amount for bulk order"""
        return sum(item.total_price for item in self.items.all())
    
    def convert_to_sale(self):
        """Convert bulk order to actual sale"""
        if self.status != 'SUBMITTED':
            return None
            
        # Create the sale
        sale = Sale.objects.create(
            customer=self.customer,
            payment_method='CASH',  # Default, can be changed later
            payment_status='PENDING',
            subtotal=self.total_amount,
            total_amount=self.total_amount,
            notes=f"Converted from bulk order {self.bulk_order_number}. {self.notes}",
            created_by=self.created_by
        )
        
        # Create sale items
        for bulk_item in self.items.all():
            SaleItem.objects.create(
                sale=sale,
                product=bulk_item.product,
                quantity=bulk_item.quantity,
                unit_price=bulk_item.unit_price,
                total_price=bulk_item.total_price
            )
        
        # Update bulk order status
        self.status = 'COMPLETED'
        self.save()
        
        return sale
    
    class Meta:
        ordering = ['-created_at']


class BulkOrderItem(models.Model):
    """Items within a bulk order"""
    bulk_order = models.ForeignKey(BulkOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.selling_price
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity} (Bulk: {self.bulk_order.bulk_order_number})"
    
    class Meta:
        unique_together = ['bulk_order', 'product']