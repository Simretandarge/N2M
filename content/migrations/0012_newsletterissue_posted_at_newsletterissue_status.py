from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0011_weekly_only_newsletter_subscribers'),
    ]

    operations = [
        migrations.AddField(
            model_name='newsletterissue',
            name='posted_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When this was posted on the site; null = not posted yet.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='newsletterissue',
            name='status',
            field=models.CharField(
                choices=[('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent')],
                default='draft',
                max_length=12,
            ),
        ),
    ]
