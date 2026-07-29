from django.db import migrations, models


def migrate_daily_to_weekly(apps, schema_editor):
    NewsletterSubscriber = apps.get_model('content', 'NewsletterSubscriber')
    NewsletterSubscriber.objects.filter(frequency='daily').update(frequency='weekly')


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0010_newslettersubscriber_frequency'),
    ]

    operations = [
        migrations.RunPython(migrate_daily_to_weekly, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='newslettersubscriber',
            name='frequency',
            field=models.CharField(
                choices=[('weekly', 'Weekly')],
                default='weekly',
                help_text='Send digest weekly (last 7 days).',
                max_length=10,
            ),
        ),
    ]
