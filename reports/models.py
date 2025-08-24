from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Report(models.Model):
    REPORT_TYPES = [
        ('DAILY_SALES', 'Daily Sales Report'),
        ('WEEKLY_SALES', 'Weekly Sales Report'),
        ('MONTHLY_SALES', 'Monthly Sales Report'),
        ('INVENTORY', 'Inventory Report'),
        ('PROFIT_LOSS', 'Profit & Loss Report'),
        ('CUSTOMER_ANALYSIS', 'Customer Analysis'),
        ('PRODUCT_PERFORMANCE', 'Product Performance'),
    ]

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    generated_at = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    is_scheduled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.generated_at.date()}"

    class Meta:
        ordering = ['-generated_at']


class ScheduledReport(models.Model):
    FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]

    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=Report.REPORT_TYPES)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    recipients = models.TextField(help_text="Comma-separated email addresses")
    next_run = models.DateTimeField()
    last_run = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.frequency}"

    class Meta:
        ordering = ['next_run']
