"""
Template context: site name, tagline, and nav categories.
"""
from django.conf import settings
from .models import Category
from .departments import DEPARTMENT_ORDER


def site_meta(request):
    """Add SITE_NAME, SITE_TAGLINE, and nav categories to template context."""
    cats_by_slug = {c.slug: c for c in Category.objects.all()}
    nav_departments = [cats_by_slug[s] for s in DEPARTMENT_ORDER if s in cats_by_slug]
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Next 251 Media'),
        'SITE_TAGLINE': getattr(settings, 'SITE_TAGLINE', 'Technology Through a Clear Lens.'),
        'SITE_DESCRIPTION': getattr(
            settings,
            'SITE_DESCRIPTION',
            'Technology, AI, Business, Startups & Innovation - explained clearly through '
            'an Ethiopian, African and global lens.',
        ),
        'NEWSLETTER_PRODUCT_NAME': getattr(settings, 'NEWSLETTER_PRODUCT_NAME', 'The Next 251 Brief'),
        'nav_categories': Category.objects.all().order_by('name'),
        'nav_departments': nav_departments,
    }
