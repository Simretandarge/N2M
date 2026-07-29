from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0013_newsletterissuemedia_postmedia_reviewmedia'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsletterIssueLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('issue', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='likes', to='content.newsletterissue')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='newsletter_issue_likes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('user', 'issue')},
            },
        ),
    ]
