from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with additional fields"""
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, required=False, help_text='Optional.')
    is_active = forms.BooleanField(required=False, initial=True, help_text='User can log in when active.')
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_active')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'Password must be at least 8 characters long.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile.html'


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    template_name = 'accounts/user_form.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('accounts:user_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'User "{self.object.username}" has been created successfully! '
            f'They can now log in with their username and password.'
        )
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
    success_url = reverse_lazy('accounts:user_list')


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Custom password change view with success message"""
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('accounts:profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been successfully changed!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class AdminPasswordResetView(LoginRequiredMixin, UpdateView):
    """Admin can reset another user's password"""
    model = User
    template_name = 'accounts/admin_password_reset.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('accounts:user_list')
    
    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs['pk'])
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.get_object()
        # Remove 'instance' from kwargs since SetPasswordForm doesn't use it
        kwargs.pop('instance', None)
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, 
            f'Password for user "{self.get_object().username}" has been reset successfully!'
        )
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


def logout_view(request):
    """Custom logout view that handles both GET and POST requests"""
    logout(request)
    return redirect('accounts:login')
