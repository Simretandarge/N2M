from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0015_post_review_instagram_post_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='newsletterissue',
            name='views',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
