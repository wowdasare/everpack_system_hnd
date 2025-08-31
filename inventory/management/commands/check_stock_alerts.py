from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import Product, StockAlert


class Command(BaseCommand):
    help = 'Check product stock levels and create alerts for low stock items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--resolve-alerts',
            action='store_true',
            help='Resolve existing alerts for items that are no longer low stock',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking stock levels...'))
        
        alerts_created = 0
        alerts_resolved = 0
        
        # Check all active products
        products = Product.objects.filter(is_active=True)
        
        for product in products:
            current_stock = product.current_stock
            
            # Check for low stock
            if current_stock <= product.minimum_stock_level:
                if current_stock == 0:
                    alert_type = 'OUT_OF_STOCK'
                    message = f'{product.name} is out of stock. Current stock: {current_stock}, Minimum required: {product.minimum_stock_level}'
                else:
                    alert_type = 'LOW_STOCK'
                    message = f'{product.name} is running low on stock. Current stock: {current_stock}, Minimum required: {product.minimum_stock_level}'
                
                # Check if alert already exists
                existing_alert = StockAlert.objects.filter(
                    product=product,
                    alert_type=alert_type,
                    is_resolved=False
                ).first()
                
                if not existing_alert:
                    StockAlert.objects.create(
                        product=product,
                        alert_type=alert_type,
                        message=message
                    )
                    alerts_created += 1
                    self.stdout.write(
                        self.style.WARNING(f'Created {alert_type} alert for {product.name}')
                    )
            
            elif options['resolve_alerts']:
                # Resolve existing alerts for products that now have sufficient stock
                resolved_alerts = StockAlert.objects.filter(
                    product=product,
                    alert_type__in=['LOW_STOCK', 'OUT_OF_STOCK'],
                    is_resolved=False
                )
                
                if resolved_alerts.exists():
                    resolved_alerts.update(
                        is_resolved=True,
                        resolved_at=timezone.now()
                    )
                    alerts_resolved += resolved_alerts.count()
                    self.stdout.write(
                        self.style.SUCCESS(f'Resolved alerts for {product.name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Stock check completed. Created {alerts_created} new alerts, resolved {alerts_resolved} alerts.'
            )
        )