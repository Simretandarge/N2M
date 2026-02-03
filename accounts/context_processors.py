"""
Expose user role (admin / editor / writer / reader) in templates.
"""
from .views import _user_role


def user_role(request):
    """Add user_role and user_role_label for the current user."""
    if request.user.is_authenticated:
        role = _user_role(request.user)
        labels = {'admin': 'Admin', 'editor': 'Editor', 'writer': 'Writer', 'reader': 'Reader'}
        return {'user_role': role, 'user_role_label': labels.get(role, 'Reader')}
    return {'user_role': None, 'user_role_label': None}
