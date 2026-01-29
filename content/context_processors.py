"""
Template context: site name, tagline, and nav categories.
"""
from django.conf import settings
from .models import Category


def site_meta(request):
    """Add SITE_NAME, SITE_TAGLINE, and nav categories to template context."""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Next 251 Media'),
        'SITE_TAGLINE': getattr(settings, 'SITE_TAGLINE', "Shaping What's Next."),
        'nav_categories': Category.objects.all().order_by('name'),
    }
