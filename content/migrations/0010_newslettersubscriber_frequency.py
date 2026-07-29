# Add subscriber preference: daily or weekly digest

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0009_add_featured_video_hero_media'),
    ]

    operations = [
        migrations.AddField(
            model_name='newslettersubscriber',
            name='frequency',
            field=models.CharField(
                choices=[('daily', 'Daily'), ('weekly', 'Weekly')],
                default='daily',
                help_text='Send digest daily (last 24h) or weekly (last 7 days).',
                max_length=10,
            ),
        ),
    ]
