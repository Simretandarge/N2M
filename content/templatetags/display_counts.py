"""Template filters for public like/save counts (logic lives in content.views)."""
from django import template

from content.models import NewsletterIssue, Post, Review
from content.views import (
    display_like_public,
    display_save_public,
    display_view_public,
    publication_time_for_boost,
)

register = template.Library()


def _kind(obj):
    if isinstance(obj, Post):
        return 'post'
    if isinstance(obj, Review):
        return 'review'
    if isinstance(obj, NewsletterIssue):
        return 'newsletter'
    return 'post'


def _published_at(obj):
    kind = _kind(obj)
    return publication_time_for_boost(obj, kind)


@register.filter
def public_like_count(obj):
    kind = _kind(obj)
    real = getattr(obj, 'like_count', None)
    if real is None:
        real = obj.likes.count()
    return display_like_public(real, obj.pk, kind, _published_at(obj))


@register.filter
def public_save_count(obj):
    kind = _kind(obj)
    real = getattr(obj, 'bookmark_count', None)
    if real is None:
        real = obj.bookmarked_by.count()
    return display_save_public(real, obj.pk, kind, _published_at(obj))


@register.filter
def public_view_count(obj):
    kind = _kind(obj)
    real_v = int(getattr(obj, 'views', 0) or 0)
    real_likes = getattr(obj, 'like_count', None)
    if real_likes is None:
        real_likes = obj.likes.count()
    return display_view_public(real_v, int(real_likes), obj.pk, kind, _published_at(obj))
