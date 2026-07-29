"""
Editorial departments for Next 251 Media navigation and homepage hubs.
"""
from django.urls import NoReverseMatch, reverse

DEPARTMENT_ORDER = ['technology', 'ai', 'business', 'startups', 'innovation']

DEPARTMENT_BLURBS = {
    'technology': 'The latest technology developments.',
    'ai': 'The companies, tools and ideas transforming AI.',
    'business': 'Companies, markets, leadership and business trends.',
    'startups': "The founders and startups building what's next.",
    'innovation': 'Ideas, research and emerging industries.',
}

CATEGORY_URL_NAMES = {
    'ai': 'content:category_ai',
    'startups': 'content:category_startups',
    'technology': 'content:category_technology',
    'business': 'content:category_business',
    'innovation': 'content:category_innovation',
}


def category_hub_url(slug: str) -> str:
    """Resolve a department slug to its public hub URL."""
    name = CATEGORY_URL_NAMES.get(slug)
    if name:
        try:
            return reverse(name)
        except NoReverseMatch:
            pass
    return reverse('content:category_detail', kwargs={'slug': slug})
