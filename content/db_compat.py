"""Detect optional DB columns so production does not 500 before migrations are applied."""
from django.db import connection

# Set once per process; restart app workers after migrating so this is re-evaluated.
_NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN = None


def newsletter_issue_has_views_column():
    """True when the NewsletterIssue table has a views column (migration applied)."""
    global _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN
    if _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN is not None:
        return _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN
    from content.models import NewsletterIssue

    table = NewsletterIssue._meta.db_table
    try:
        with connection.cursor() as cursor:
            cols = connection.introspection.get_table_description(cursor, table)
        names = {getattr(c, 'name', c[0]).lower() for c in cols}
        _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN = 'views' in names
    except Exception:
        _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN = False
    return _NEWSLETTER_ISSUE_HAS_VIEWS_COLUMN
