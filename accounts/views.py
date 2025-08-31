from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.views import PasswordChangeView, LoginView
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import get_object_or_404
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .templatetags.role_tags import get_user_role
from django.http import Http404


class CustomLoginView(LoginView):
    """Custom login view with password confirmation"""
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().get_full_name() or form.get_user().username}!')
        return super().form_valid(form)




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


class UserDeleteView(LoginRequiredMixin, DeleteView):
    """Admin can delete users (except themselves)"""
    model = User
    success_url = reverse_lazy('accounts:user_list')
    
    def dispatch(self, request, *args, **kwargs):
        # Only admins can delete users
        if get_user_role(request.user) != 'admin':
            raise Http404("You don't have permission to delete users")
        
        # Can't delete yourself
        if self.get_object() == request.user:
            messages.error(request, "You cannot delete your own account!")
            return redirect('accounts:user_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        user_to_delete = self.get_object()
        username = user_to_delete.username
        
        # Delete the user
        self.object = user_to_delete
        user_to_delete.delete()
        
        messages.success(request, f'User "{username}" has been deleted successfully!')
        return redirect(self.success_url)


def logout_view(request):
    """Custom logout view that handles both GET and POST requests"""
    logout(request)
    return redirect('accounts:login')
