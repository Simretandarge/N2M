# Generated manually for featured_video and hero_image/hero_video

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0008_review_like_review_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='featured_video',
            field=models.FileField(blank=True, null=True, upload_to='posts/videos/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='review',
            name='featured_video',
            field=models.FileField(blank=True, null=True, upload_to='reviews/videos/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='newsletterissue',
            name='hero_image',
            field=models.ImageField(blank=True, null=True, upload_to='newsletters/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='newsletterissue',
            name='hero_video',
            field=models.FileField(blank=True, null=True, upload_to='newsletters/videos/%Y/%m/'),
        ),
    ]
