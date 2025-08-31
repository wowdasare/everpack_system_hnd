from django import forms
from django.forms import inlineformset_factory
from .models import Sale, SaleItem, Customer
from inventory.models import Product


class SaleForm(forms.ModelForm):
    """Form for creating/editing sales"""
    
    class Meta:
        model = Sale
        fields = ['customer', 'payment_method', 'payment_status', 'discount_amount', 'tax_amount', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_status': forms.Select(attrs={'class': 'form-control'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SaleItemForm(forms.ModelForm):
    """Form for individual sale items"""
    
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price-input', 'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active products
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        
        # Set unit price from product if not provided
        if self.instance and self.instance.product:
            if not self.instance.unit_price:
                self.fields['unit_price'].initial = self.instance.product.selling_price


# Create formset for multiple sale items
SaleItemFormSet = inlineformset_factory(
    Sale, 
    SaleItem, 
    form=SaleItemForm,
    extra=1,  # Number of empty forms to display
    min_num=1,  # Minimum number of forms required
    validate_min=True,
    can_delete=True
)