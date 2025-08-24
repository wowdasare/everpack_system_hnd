from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from .models import Sale, Customer, Payment, SaleItem
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
        from django.utils import timezone
        from django.db.models import Sum
        
        today = timezone.now().date()
        
        # Calculate today's sales (only paid)
        today_sales = Sale.objects.filter(
            sale_date__date=today,
            payment_status='PAID'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate total revenue (all paid sales)
        total_revenue = Sale.objects.filter(
            payment_status='PAID'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate pending payments
        pending_payments = Sale.objects.filter(
            payment_status__in=['PENDING', 'PARTIAL']
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
    template_name = 'sales/sale_form.html'
    fields = ['customer', 'payment_method', 'payment_status', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'amount_paid', 'notes']
    success_url = reverse_lazy('sales:sale_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Sale {self.object.invoice_number} has been created successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        print("Form errors:", form.errors)  # Debug print
        return super().form_invalid(form)


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    model = Sale
    template_name = 'sales/sale_form.html'
    fields = ['customer', 'payment_method', 'payment_status', 'subtotal', 'discount_amount', 'tax_amount', 'total_amount', 'amount_paid', 'notes']
    
    def form_valid(self, form):
        messages.success(self.request, f'Sale {form.instance.invoice_number} has been updated successfully!')
        return super().form_valid(form)
    
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
    
    # Items
    for item in sale.items.all():
        item_line = f"{item.product.name} x {item.quantity}"
        price_line = f"GHS {item.total_price:.2f}"
        elements.append(Paragraph(item_line, receipt_style))
        elements.append(Paragraph(price_line, ParagraphStyle(
            'Price', parent=receipt_style, alignment=2)))  # Right align
    
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
    return JsonResponse({'price': 0})


def customer_search(request):
    return JsonResponse({'customers': []})
