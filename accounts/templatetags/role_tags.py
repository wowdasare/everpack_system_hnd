from django import template
from django.contrib.auth.models import Group

register = template.Library()


@register.filter
def has_role(user, role_name):
    """Check if user has a specific role"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    return user.groups.filter(name=role_name).exists()


@register.filter
def get_user_role(user):
    """Get user's primary role"""
    if not user or not user.is_authenticated:
        return None
    
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


@register.simple_tag
def can_access_app(user, app_name):
    """Check if user can access a specific app"""
    role = get_user_role(user)
    
    role_permissions = {
        'admin': ['dashboard', 'inventory', 'sales', 'reports', 'accounts'],
        'manager': ['dashboard', 'inventory', 'sales', 'reports', 'accounts'],
        'sales_rep': ['dashboard', 'inventory', 'sales']
    }
    
    if not role or role not in role_permissions:
        return False
    
    return app_name in role_permissions[role]


@register.simple_tag
def can_perform_action(user, action):
    """Check if user can perform a specific action"""
    role = get_user_role(user)
    
    role_actions = {
        'admin': ['view', 'add', 'change', 'delete'],
        'manager': ['view', 'add', 'change'],
        'sales_rep': ['view', 'add', 'change']
    }
    
    if not role or role not in role_actions:
        return False
    
    return action in role_actions[role]


@register.simple_tag  
def can_manage_stock(user):
    """Check if user can manage stock/inventory operations"""
    role = get_user_role(user)
    
    # Only admins and managers can manage stock
    return role in ['admin', 'manager']


@register.simple_tag
def can_delete_users(user):
    """Check if user can delete other users"""
    role = get_user_role(user)
    
    # Only admins can delete users
    return role == 'admin'