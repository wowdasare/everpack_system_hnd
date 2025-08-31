from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form with Bootstrap styling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with additional fields"""
    USER_TYPES = [
        ('admin', 'Administrator'),
        ('sales_rep', 'Sales Representative'),
        ('manager', 'Manager'),
    ]
    
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, required=False, help_text='Optional.')
    is_active = forms.BooleanField(required=False, initial=True, help_text='User can log in when active.')
    user_type = forms.ChoiceField(choices=USER_TYPES, required=True, help_text='Select user role')
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_active', 'user_type')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'Password must be at least 8 characters long.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user_type = self.cleaned_data.get('user_type')
        
        # Set permissions based on user type
        if user_type == 'admin':
            user.is_staff = True
            user.is_superuser = True
        elif user_type == 'manager':
            user.is_staff = True
            user.is_superuser = False
        else:  # sales_rep
            user.is_staff = False
            user.is_superuser = False
        
        if commit:
            user.save()
            # Store user type in user profile or session
            # For now, we'll use the user's groups
            from django.contrib.auth.models import Group
            group, created = Group.objects.get_or_create(name=user_type)
            user.groups.add(group)
        
        return user