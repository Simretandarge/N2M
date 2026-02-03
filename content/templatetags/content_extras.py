"""
Template tags for content: reading time, etc.
"""
from django import template

register = template.Library()

# Average reading speed (words per minute)
WORDS_PER_MINUTE = 200


@register.filter
def reading_time(text):
    """Estimate reading time in minutes from plain text. Returns e.g. '3 min read'."""
    if not text:
        return "1 min read"
    word_count = len(text.split())
    minutes = max(1, round(word_count / WORDS_PER_MINUTE))
    if minutes == 1:
        return "1 min read"
    return f"{minutes} min read"
