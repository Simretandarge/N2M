from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0012_newsletterissue_posted_at_newsletterissue_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsletterIssueMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='newsletters/gallery/%Y/%m/')),
                ('video', models.FileField(blank=True, null=True, upload_to='newsletters/videos/gallery/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='content.newsletterissue')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PostMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='posts/gallery/%Y/%m/')),
                ('video', models.FileField(blank=True, null=True, upload_to='posts/videos/gallery/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='content.post')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReviewMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to='reviews/gallery/%Y/%m/')),
                ('video', models.FileField(blank=True, null=True, upload_to='reviews/videos/gallery/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media_items', to='content.review')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
