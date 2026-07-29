from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from content.models import NewsletterSubscriber


@receiver(post_save, sender=get_user_model())
def auto_subscribe_new_users(sender, instance, created, **kwargs):
    """Automatically subscribe newly created users to the weekly newsletter."""
    if not created or not instance.email:
        return
    NewsletterSubscriber.objects.get_or_create(
        email=instance.email,
        defaults={'frequency': NewsletterSubscriber.FREQUENCY_WEEKLY},
    )
