from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0014_newsletterissuelike'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='instagram_post_url',
            field=models.URLField(
                blank=True,
                help_text='Optional. Permalink to this story on @next251media (e.g. https://www.instagram.com/p/… or /reel/…). Used by the site “Share → Instagram” action.',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='review',
            name='instagram_post_url',
            field=models.URLField(
                blank=True,
                help_text='Optional. Permalink to this review on @next251media (Instagram post or reel URL).',
                max_length=500,
            ),
        ),
    ]
