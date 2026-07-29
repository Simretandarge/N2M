"""
Expose user role (admin / editor / writer / reader) in templates.
"""
from .views import _user_role
from .models import UserProfile


def user_role(request):
    """Add user_role and user_role_label for the current user."""
    if request.user.is_authenticated:
        role = _user_role(request.user)
        labels = {'admin': 'Admin', 'editor': 'Editor', 'writer': 'Writer', 'reader': 'Reader'}
        try:
            profile = UserProfile.objects.filter(user=request.user).only('photo').first()
        except Exception:
            profile = None
        photo_url = profile.photo.url if profile and profile.photo else None
        return {
            'user_role': role,
            'user_role_label': labels.get(role, 'Reader'),
            'nav_profile_photo_url': photo_url,
        }
    return {'user_role': None, 'user_role_label': None, 'nav_profile_photo_url': None}
