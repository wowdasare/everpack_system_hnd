from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import Group


class RoleBasedAccessMiddleware:
    """Middleware to control access based on user roles"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Define role-based permissions
        self.role_permissions = {
            'admin': {
                'allowed_apps': ['dashboard', 'inventory', 'sales', 'reports', 'accounts'],
                'allowed_actions': ['view', 'add', 'change', 'delete'],
                'restricted_paths': []
            },
            'manager': {
                'allowed_apps': ['dashboard', 'inventory', 'sales', 'reports', 'accounts'],
                'allowed_actions': ['view', 'add', 'change', 'delete'],
                'restricted_paths': ['/Admin/']
            },
            'sales_rep': {
                'allowed_apps': ['dashboard', 'inventory', 'sales'],
                'allowed_actions': ['view', 'add', 'change'],
                'restricted_paths': ['/inventory/stock-movements/', '/reports/', '/accounts/users/', '/Admin/']
            }
        }

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for unauthenticated users and login/logout views
        if not request.user.is_authenticated:
            return None
            
        if request.path.startswith('/accounts/login/') or request.path.startswith('/accounts/logout/'):
            return None
        
        # Check if user is superuser (admin)
        if request.user.is_superuser:
            return None
            
        # Determine user role
        user_role = self.get_user_role(request.user)
        
        if not user_role:
            messages.error(request, 'Your account does not have a valid role assigned.')
            return redirect('accounts:login')
        
        # Check path permissions
        if self.is_path_restricted(request.path, user_role):
            messages.error(request, 'You do not have permission to access this page.')
            
            # Avoid redirect loops - if user can't access dashboard, redirect to appropriate page
            if 'dashboard' in self.role_permissions[user_role]['allowed_apps']:
                return redirect('dashboard:home')
            elif 'sales' in self.role_permissions[user_role]['allowed_apps']:
                return redirect('sales:sale_list')
            else:
                return redirect('accounts:login')
        
        return None
    
    def get_user_role(self, user):
        """Get user role from groups"""
        if user.is_superuser:
            return 'admin'
        
        user_groups = user.groups.values_list('name', flat=True)
        
        if 'admin' in user_groups:
            return 'admin'
        elif 'manager' in user_groups:
            return 'manager'
        elif 'sales_rep' in user_groups:
            return 'sales_rep'
        
        return None
    
    def is_path_restricted(self, path, user_role):
        """Check if path is restricted for user role"""
        if user_role not in self.role_permissions:
            return True
        
        role_config = self.role_permissions[user_role]
        
        # Check if path is in restricted paths
        for restricted_path in role_config['restricted_paths']:
            if path.startswith(restricted_path):
                return True
        
        return False