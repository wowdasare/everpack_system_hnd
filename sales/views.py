from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from .models import Sale, Customer, Payment, SaleItem, BulkOrder, BulkOrderItem
from .forms import SaleForm, SaleItemFormSet
from inventory.models import Product
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import io


class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sale_list.html'
    context_object_name = 'sales'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Sum
        
        today = timezone.now().date()
        
        # Calculate today's sales (all sales for today)
        today_sales = Sale.objects.filter(
            sale_date__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate total revenue (actual amount received from all sales)
        total_revenue = Sale.objects.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Calculate pending payments (sales with outstanding balance)
        from django.db.models import Q
        pending_payments = Sale.objects.filter(
            Q(total_amount__gt=models.F('amount_paid')) & Q(total_amount__gt=0)
        ).count()
        
        context['today_sales'] = f"GHS {today_sales:.2f}"
        context['total_revenue'] = f"GHS {total_revenue:.2f}"
        context['pending_payments'] = pending_payments
        
        return context


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = 'sales/sale_detail.html'
    context_object_name = 'sale'


class SaleCreateView(LoginRequiredMixin, CreateView):
    model = Sale
    template_name = 'sales/sale_form_complete.html'
    fields = ['customer', 'payment_method', 'payment_status', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'amount_paid', 'notes']
    success_url = reverse_lazy('sales:sale_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        context['customers'] = Customer.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        from django.db import transaction
        
        form.instance.created_by = self.request.user
        
        # Enforce today's date for new sales (strict invoice date policy)
        if not form.instance.pk:  # New sale
            form.instance.sale_date = timezone.now()
        
        # Validate that sale is for today only
        try:
            form.instance.clean()
        except ValidationError as e:
            error_message = 'Cannot create invoices for previous dates. Invoices can only be generated for the current day.'
            if hasattr(e, 'message_dict'):
                for field_errors in e.message_dict.values():
                    error_message = field_errors[0] if field_errors else error_message
            form.add_error(None, error_message)
            return self.form_invalid(form)
        
        # Extract items data from the POST request
        items_data = self.extract_items_from_request()
        
        if not items_data:
            form.add_error(None, 'Please add at least one product to the sale.')
            return self.form_invalid(form)
        
        # Save the sale and items in a transaction
        try:
            with transaction.atomic():
                # Save the sale
                response = super().form_valid(form)
                
                # Create sale items
                for item_data in items_data:
                    try:
                        product = Product.objects.get(id=item_data['product'], is_active=True)
                        SaleItem.objects.create(
                            sale=self.object,
                            product=product,
                            quantity=item_data['quantity'],
                            unit_price=item_data['unit_price']
                        )
                    except Product.DoesNotExist:
                        raise ValidationError(f'Product with ID {item_data["product"]} not found')
                
                # Recalculate totals
                self.object.calculate_totals()
                
                messages.success(
                    self.request, 
                    f'Sale {self.object.invoice_number} has been created successfully with {len(items_data)} items!'
                )
                return response
                
        except Exception as e:
            print(f"Error saving sale: {e}")
            form.add_error(None, f'Error saving sale: {str(e)}')
            return self.form_invalid(form)
    
    def extract_items_from_request(self):
        """Extract items data from the POST request"""
        items_data = []
        post_data = self.request.POST
        
        # Find all item entries in the form data
        item_keys = set()
        for key in post_data.keys():
            if key.startswith('items[') and '][' in key:
                item_num = key.split('[')[1].split(']')[0]
                item_keys.add(item_num)
        
        # Extract data for each item
        for item_num in item_keys:
            product_key = f'items[{item_num}][product]'
            quantity_key = f'items[{item_num}][quantity]'
            price_key = f'items[{item_num}][unit_price]'
            
            if (product_key in post_data and quantity_key in post_data and price_key in post_data):
                try:
                    product_id = post_data[product_key]
                    quantity = post_data[quantity_key]
                    unit_price = post_data[price_key]
                    
                    if product_id and quantity and unit_price:
                        product_id = int(product_id)
                        quantity = int(quantity)
                        unit_price = float(unit_price)
                        
                        if product_id > 0 and quantity > 0 and unit_price >= 0:
                            items_data.append({
                                'product': product_id,
                                'quantity': quantity,
                                'unit_price': unit_price
                            })
                except (ValueError, TypeError):
                    continue
        
        return items_data
    
    def form_invalid(self, form):
        print(f"Form errors: {form.errors}")
        print(f"Form non-field errors: {form.non_field_errors()}")
        
        # Get specific error messages
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    error_messages.append(str(error))
                else:
                    error_messages.append(f'{field}: {error}')
        
        if error_messages:
            messages.error(self.request, 'Errors: ' + '; '.join(error_messages))
        else:
            messages.error(self.request, 'Please correct the errors below.')
        
        return super().form_invalid(form)


class SaleCreateSimpleView(LoginRequiredMixin, CreateView):
    model = Sale
    template_name = 'sales/sale_form.html'
    fields = ['customer', 'payment_method', 'payment_status', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'amount_paid', 'notes']
    success_url = reverse_lazy('sales:sale_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Validate that sale is for today only
        try:
            form.instance.clean()
        except ValidationError as e:
            form.add_error(None, e.message_dict if hasattr(e, 'message_dict') else str(e))
            return self.form_invalid(form)
        
        # Save the sale
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Sale {self.object.invoice_number} has been created successfully! You can now add items to this sale.')
            return response
        except Exception as e:
            form.add_error(None, f'Error saving sale: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Get specific error messages
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    error_messages.append(str(error))
                else:
                    error_messages.append(f'{field}: {error}')
        
        if error_messages:
            messages.error(self.request, 'Errors: ' + '; '.join(error_messages))
        else:
            messages.error(self.request, 'Please correct the errors below.')
        
        return super().form_invalid(form)


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    model = Sale
    template_name = 'sales/sale_form.html'
    fields = ['customer', 'payment_method', 'payment_status', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'amount_paid', 'notes']
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Check if the sale is from today
        today = timezone.now().date()
        sale_date = obj.sale_date.date()
        
        if sale_date != today:
            messages.error(self.request, 
                          f'Cannot edit invoices from previous dates. '
                          f'Invoice {obj.invoice_number} is from {sale_date.strftime("%Y-%m-%d")}. '
                          f'Only payment updates are allowed on old invoices.')
            from django.shortcuts import redirect
            return redirect('sales:sale_detail', pk=obj.pk)
        
        return obj
    
    def form_valid(self, form):
        # Additional validation in form_valid
        try:
            form.instance.clean()
            messages.success(self.request, f'Sale {form.instance.invoice_number} has been updated successfully!')
            return super().form_valid(form)
        except ValidationError as e:
            error_message = str(e.message_dict) if hasattr(e, 'message_dict') else str(e)
            messages.error(self.request, f'Cannot update sale: {error_message}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SaleItemCreateView(LoginRequiredMixin, CreateView):
    model = SaleItem
    template_name = 'sales/sale_item_form.html'
    fields = ['product', 'quantity', 'unit_price']
    
    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, pk=self.kwargs['sale_pk'])
        
        # Prevent adding items to old sales
        today = timezone.now().date()
        sale_date = self.sale.sale_date.date()
        
        if sale_date != today:
            messages.error(request, 
                          f'Cannot add items to invoices from previous dates. '
                          f'Invoice {self.sale.invoice_number} is from {sale_date.strftime("%Y-%m-%d")}. '
                          f'Items can only be added to today\'s invoices.')
            return redirect('sales:sale_detail', pk=self.sale.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sale'] = self.sale
        context['products'] = Product.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        form.instance.sale = self.sale
        if not form.instance.unit_price:
            form.instance.unit_price = form.instance.product.selling_price
        
        response = super().form_valid(form)
        
        # Recalculate sale totals
        self.sale.calculate_totals()
        
        messages.success(self.request, f'Item "{self.object.product.name}" added to sale {self.sale.invoice_number}!')
        return redirect('sales:sale_detail', pk=self.sale.pk)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'sales/customer_list.html'
    context_object_name = 'customers'


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'sales/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_sales_count'] = self.object.sales.filter(payment_status='PENDING').count()
        # Calculate credit utilization percentage
        if self.object.credit_limit > 0:
            context['credit_usage_percent'] = min(100, (self.object.outstanding_balance / self.object.credit_limit) * 100)
        else:
            context['credit_usage_percent'] = 0
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    template_name = 'sales/customer_form.html'
    fields = ['name', 'customer_type', 'phone', 'email', 'address', 'tin_number', 'credit_limit', 'is_active']
    success_url = reverse_lazy('sales:customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" has been created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    template_name = 'sales/customer_form.html'
    fields = ['name', 'customer_type', 'phone', 'email', 'address', 'tin_number', 'credit_limit', 'is_active']
    success_url = reverse_lazy('sales:customer_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Customer "{form.instance.name}" has been updated successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'sales/payment_list.html'
    context_object_name = 'payments'


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    template_name = 'sales/payment_form.html'
    fields = ['sale', 'amount', 'payment_method', 'reference_number', 'notes', 'created_by']
    success_url = reverse_lazy('sales:payment_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Set current user as default
        initial['created_by'] = self.request.user
        
        # If sale_id is provided in URL, set it as default
        sale_id = self.kwargs.get('sale_id')
        if sale_id:
            initial['sale'] = sale_id
            
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Update the sale's payment status and amount_paid
        sale = form.instance.sale
        total_payments = sale.payments.aggregate(total=models.Sum('amount'))['total'] or 0
        sale.amount_paid = total_payments
        
        # Update payment status
        if sale.amount_paid >= sale.total_amount:
            sale.payment_status = 'PAID'
        elif sale.amount_paid > 0:
            sale.payment_status = 'PARTIAL'
        else:
            sale.payment_status = 'PENDING'
            
        sale.save()
        
        messages.success(self.request, f'Payment of GHS {form.instance.amount} has been processed successfully for {sale.invoice_number}!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def invoice_pdf(request, pk):
    """Generate invoice PDF for a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    invoice_header_style = ParagraphStyle(
        'InvoiceHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=0,  # Left alignment
        textColor=colors.darkblue
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )
    
    # Company Header
    title = Paragraph("EverPack System", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Invoice Header
    invoice_header = Paragraph(f"INVOICE #{sale.invoice_number}", invoice_header_style)
    elements.append(invoice_header)
    elements.append(Spacer(1, 12))
    
    # Company and Customer Info using Paragraphs for proper formatting
    company_info = Paragraph(
        "<b>EverPack System</b><br/>Packaging &amp; Wholesale<br/>Accra, Ghana<br/>Phone: +233 200 000 000<br/>Email: info@everpack.com",
        normal_style
    )
    
    # Format customer info with proper handling of empty fields
    customer_parts = [f"<b>{sale.customer.name}</b>"]
    if sale.customer.address:
        customer_address = sale.customer.address.replace('\n', '<br/>')
        customer_parts.append(customer_address)
    if sale.customer.phone:
        customer_parts.append(f"Phone: {sale.customer.phone}")
    if sale.customer.email:
        customer_parts.append(f"Email: {sale.customer.email}")
    
    customer_info = Paragraph('<br/>'.join(customer_parts), normal_style)
    
    info_data = [
        ['From:', 'To:'],
        [company_info, customer_info],
        ['', ''],
        ['Invoice Date:', f'{sale.sale_date.strftime("%B %d, %Y")}'],
        ['Payment Method:', sale.get_payment_method_display()],
        ['Payment Status:', sale.get_payment_status_display()],
    ]
    
    info_table = Table(info_data, colWidths=[3*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Items Table
    items_data = [['Item', 'SKU', 'Qty', 'Unit Price (GHS)', 'Total (GHS)']]
    
    total_amount = 0
    for item in sale.items.all():
        items_data.append([
            item.product.name,
            item.product.sku,
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{item.total_price:.2f}"
        ])
        total_amount += item.total_price
    
    # Add summary rows
    items_data.append(['', '', '', 'Subtotal:', f"{sale.subtotal:.2f}"])
    if sale.discount_amount > 0:
        items_data.append(['', '', '', 'Discount:', f"-{sale.discount_amount:.2f}"])
    if sale.tax_amount > 0:
        items_data.append(['', '', '', 'Tax:', f"{sale.tax_amount:.2f}"])
    items_data.append(['', '', '', 'TOTAL:', f"{sale.total_amount:.2f}"])
    
    if sale.payment_status != 'PAID':
        items_data.append(['', '', '', 'Amount Paid:', f"{sale.amount_paid:.2f}"])
        items_data.append(['', '', '', 'Balance Due:', f"{sale.balance_due:.2f}"])
    
    items_table = Table(items_data, colWidths=[2.5*inch, 1*inch, 0.7*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Quantity column
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Price columns
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        # Summary rows styling
        ('BACKGROUND', (0, -3), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -3), (-1, -3), 2, colors.black),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('LINEBELOW', (0, -4), (-1, -4), 2, colors.black),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 30))
    
    # Notes section
    if sale.notes:
        notes_para = Paragraph(f"<b>Notes:</b><br/>{sale.notes}", normal_style)
        elements.append(notes_para)
        elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = "Thank you for your business!<br/><br/>This is a computer generated invoice."
    footer_para = Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,  # Center alignment
        textColor=colors.grey
    ))
    elements.append(footer_para)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data and create response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{sale.invoice_number}.pdf"'
    response.write(pdf)
    
    return response


def receipt_pdf(request, pk):
    """Generate receipt PDF for a sale"""
    sale = get_object_or_404(Sale, pk=pk)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(4*inch, 6*inch), rightMargin=0.2*inch, 
                           leftMargin=0.2*inch, topMargin=0.2*inch, bottomMargin=0.2*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Receipt style
    receipt_style = ParagraphStyle(
        'Receipt',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,  # Center alignment
        spaceAfter=3,
    )
    
    # Header
    elements.append(Paragraph("EverPack System", ParagraphStyle(
        'ReceiptHeader', parent=receipt_style, fontSize=12, fontName='Helvetica-Bold')))
    elements.append(Paragraph("Packaging & Wholesale", receipt_style))
    elements.append(Paragraph("Accra, Ghana", receipt_style))
    elements.append(Spacer(1, 6))
    
    # Receipt info
    elements.append(Paragraph(f"Receipt: {sale.invoice_number}", ParagraphStyle(
        'ReceiptNumber', parent=receipt_style, fontSize=10, fontName='Helvetica-Bold')))
    elements.append(Paragraph(f"Date: {sale.sale_date.strftime('%Y-%m-%d %H:%M')}", receipt_style))
    elements.append(Paragraph(f"Customer: {sale.customer.name}", receipt_style))
    elements.append(Spacer(1, 6))
    
    # Divider
    elements.append(Paragraph("=" * 40, receipt_style))
    
    # Items Header
    elements.append(Paragraph("ITEMS PURCHASED:", ParagraphStyle(
        'ItemsHeader', parent=receipt_style, fontSize=9, fontName='Helvetica-Bold')))
    elements.append(Spacer(1, 3))
    
    # Items
    for item in sale.items.all():
        # Product name and quantity
        item_line = f"{item.product.name}"
        elements.append(Paragraph(item_line, receipt_style))
        
        # Quantity, unit price and total on separate line
        detail_line = f"{item.quantity} x GHS {item.unit_price:.2f} = GHS {item.total_price:.2f}"
        elements.append(Paragraph(detail_line, ParagraphStyle(
            'ItemDetail', parent=receipt_style, fontSize=7, alignment=2)))  # Right align
        
        # Small space between items
        elements.append(Spacer(1, 2))
    
    elements.append(Paragraph("=" * 40, receipt_style))
    
    # Total
    elements.append(Paragraph(f"TOTAL: GHS {sale.total_amount:.2f}", ParagraphStyle(
        'Total', parent=receipt_style, fontSize=10, fontName='Helvetica-Bold')))
    
    if sale.payment_status != 'PAID':
        elements.append(Paragraph(f"Paid: GHS {sale.amount_paid:.2f}", receipt_style))
        elements.append(Paragraph(f"Balance: GHS {sale.balance_due:.2f}", receipt_style))
    
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Thank you!", receipt_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data and create response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{sale.invoice_number}.pdf"'
    response.write(pdf)
    
    return response


def get_product_price(request):
    """AJAX endpoint to get product price and stock info"""
    product_id = request.GET.get('product_id')
    if product_id:
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            return JsonResponse({
                'price': float(product.selling_price),
                'cost_price': float(product.cost_price),
                'current_stock': product.current_stock,
                'minimum_stock': product.minimum_stock_level,
                'is_low_stock': product.is_low_stock,
                'unit': product.get_unit_display(),
            })
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'No product ID provided'}, status=400)


def customer_search(request):
    return JsonResponse({'customers': []})


class BulkOrderListView(LoginRequiredMixin, ListView):
    model = BulkOrder
    template_name = 'sales/bulk_order_list.html'
    context_object_name = 'bulk_orders'
    
    def get_queryset(self):
        # Sales reps can only see their own bulk orders
        if self.request.user.groups.filter(name='sales_rep').exists() and not self.request.user.is_superuser:
            return BulkOrder.objects.filter(created_by=self.request.user)
        return BulkOrder.objects.all()


class BulkOrderDetailView(LoginRequiredMixin, DetailView):
    model = BulkOrder
    template_name = 'sales/bulk_order_detail.html'
    context_object_name = 'bulk_order'
    
    def get_queryset(self):
        # Sales reps can only see their own bulk orders
        if self.request.user.groups.filter(name='sales_rep').exists() and not self.request.user.is_superuser:
            return BulkOrder.objects.filter(created_by=self.request.user)
        return BulkOrder.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(is_active=True)
        return context
    
    def post(self, request, *args, **kwargs):
        bulk_order = self.get_object()
        action = request.POST.get('action')
        
        if action == 'add_item' and bulk_order.status == 'DRAFT':
            try:
                product_id = request.POST.get('product')
                quantity = int(request.POST.get('quantity'))
                unit_price = float(request.POST.get('unit_price'))
                
                product = Product.objects.get(id=product_id, is_active=True)
                
                # Check if item already exists
                existing_item = bulk_order.items.filter(product=product).first()
                if existing_item:
                    existing_item.quantity += quantity
                    existing_item.total_price = existing_item.quantity * existing_item.unit_price
                    existing_item.save()
                    messages.success(request, f'Updated quantity for {product.name}')
                else:
                    BulkOrderItem.objects.create(
                        bulk_order=bulk_order,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price
                    )
                    messages.success(request, f'Added {product.name} to bulk order')
                    
            except (ValueError, Product.DoesNotExist) as e:
                messages.error(request, f'Error adding item: {str(e)}')
                
        elif action == 'remove_item' and bulk_order.status == 'DRAFT':
            try:
                item_id = request.POST.get('item_id')
                item = BulkOrderItem.objects.get(id=item_id, bulk_order=bulk_order)
                product_name = item.product.name
                item.delete()
                messages.success(request, f'Removed {product_name} from bulk order')
            except BulkOrderItem.DoesNotExist:
                messages.error(request, 'Item not found')
        
        return redirect('sales:bulk_order_detail', pk=bulk_order.pk)


class BulkOrderCreateView(LoginRequiredMixin, CreateView):
    model = BulkOrder
    template_name = 'sales/bulk_order_form.html'
    fields = ['customer', 'notes']
    success_url = reverse_lazy('sales:bulk_order_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Bulk Order {self.object.bulk_order_number} has been created successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class BulkOrderUpdateView(LoginRequiredMixin, UpdateView):
    model = BulkOrder
    template_name = 'sales/bulk_order_form.html'
    fields = ['customer', 'notes', 'status']
    success_url = reverse_lazy('sales:bulk_order_list')
    
    def get_queryset(self):
        # Sales reps can only edit their own bulk orders
        if self.request.user.groups.filter(name='sales_rep').exists() and not self.request.user.is_superuser:
            return BulkOrder.objects.filter(created_by=self.request.user)
        return BulkOrder.objects.all()
    
    def form_valid(self, form):
        # Handle status change to submitted
        if form.instance.status == 'SUBMITTED' and not form.instance.submitted_at:
            form.instance.submitted_at = timezone.now()
            
        response = super().form_valid(form)
        messages.success(self.request, f'Bulk Order {form.instance.bulk_order_number} has been updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def convert_bulk_order_to_sale(request, pk):
    """Convert a bulk order to an actual sale"""
    bulk_order = get_object_or_404(BulkOrder, pk=pk)
    
    # Check permissions
    if request.user.groups.filter(name='sales_rep').exists() and not request.user.is_superuser:
        if bulk_order.created_by != request.user:
            messages.error(request, 'You can only convert your own bulk orders.')
            return redirect('sales:bulk_order_list')
    
    if bulk_order.status != 'SUBMITTED':
        messages.error(request, 'Only submitted bulk orders can be converted to sales.')
        return redirect('sales:bulk_order_detail', pk=pk)
    
    if not bulk_order.items.exists():
        messages.error(request, 'Cannot convert bulk order with no items.')
        return redirect('sales:bulk_order_detail', pk=pk)
    
    try:
        sale = bulk_order.convert_to_sale()
        if sale:
            messages.success(request, f'Bulk Order {bulk_order.bulk_order_number} has been converted to Sale {sale.invoice_number}!')
            return redirect('sales:sale_detail', pk=sale.pk)
        else:
            messages.error(request, 'Failed to convert bulk order to sale.')
    except Exception as e:
        messages.error(request, f'Error converting bulk order: {str(e)}')
    
    return redirect('sales:bulk_order_detail', pk=pk)


def bulk_order_receipt_pdf(request, pk):
    """Generate receipt PDF for a bulk order"""
    bulk_order = get_object_or_404(BulkOrder, pk=pk)
    
    # Check permissions
    if request.user.groups.filter(name='sales_rep').exists() and not request.user.is_superuser:
        if bulk_order.created_by != request.user:
            messages.error(request, 'You can only generate receipts for your own bulk orders.')
            return redirect('sales:bulk_order_list')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )
    
    # Company Header
    title = Paragraph("EverPack System", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Bulk Order Header
    bulk_order_header = Paragraph(f"BULK ORDER #{bulk_order.bulk_order_number}", ParagraphStyle(
        'BulkOrderHeader', parent=styles['Heading2'], fontSize=16, spaceAfter=20,
        alignment=0, textColor=colors.darkblue))
    elements.append(bulk_order_header)
    elements.append(Spacer(1, 12))
    
    # Information table
    info_data = [
        ['Customer:', bulk_order.customer.name],
        ['Status:', bulk_order.get_status_display()],
        ['Created Date:', bulk_order.created_at.strftime("%B %d, %Y")],
        ['Created By:', bulk_order.created_by.get_full_name() or bulk_order.created_by.username],
    ]
    
    if bulk_order.submitted_at:
        info_data.append(['Submitted Date:', bulk_order.submitted_at.strftime("%B %d, %Y")])
    
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib.units import inch
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Items Table
    items_data = [['Item', 'SKU', 'Qty', 'Unit Price (GHS)', 'Total (GHS)']]
    
    for item in bulk_order.items.all():
        items_data.append([
            item.product.name,
            item.product.sku,
            str(item.quantity),
            f"{item.unit_price:.2f}",
            f"{item.total_price:.2f}"
        ])
    
    # Add total row
    items_data.append(['', '', '', 'TOTAL:', f"{bulk_order.total_amount:.2f}"])
    
    items_table = Table(items_data, colWidths=[2.5*inch, 1*inch, 0.7*inch, 1.2*inch, 1.2*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Quantity column
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Price columns
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('LINEBELOW', (0, -2), (-1, -2), 2, colors.black),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 30))
    
    # Notes section
    if bulk_order.notes:
        notes_para = Paragraph(f"<b>Notes:</b><br/>{bulk_order.notes}", normal_style)
        elements.append(notes_para)
        elements.append(Spacer(1, 20))
    
    # Footer
    footer_text = "Thank you for your business!<br/><br/>This is a computer generated bulk order summary."
    footer_para = Paragraph(footer_text, ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=9, alignment=1,
        textColor=colors.grey))
    elements.append(footer_para)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data and create response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bulk_order_{bulk_order.bulk_order_number}.pdf"'
    response.write(pdf)
    
    return response
