"""Ensure editorial department categories exist (Technology, AI, Business, Startups, Innovation)."""
from django.db import migrations


DEPARTMENTS = [
    ('technology', 'Technology'),
    ('ai', 'AI'),
    ('business', 'Business'),
    ('startups', 'Startups'),
    ('innovation', 'Innovation'),
]


def create_departments(apps, schema_editor):
    Category = apps.get_model('content', 'Category')
    for slug, name in DEPARTMENTS:
        Category.objects.get_or_create(slug=slug, defaults={'name': name})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0016_newsletterissue_views'),
    ]

    operations = [
        migrations.RunPython(create_departments, noop),
    ]
