"""
Account-related models: editor applications.
"""
from django.conf import settings
from django.db import models


class EditorApplication(models.Model):
    """Writer's request to become an editor. Admins approve or reject."""
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='editor_applications',
    )
    message = models.TextField(
        blank=True,
        help_text='Why you want to become an editor (optional).',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_editor_applications',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_username()} — {self.get_status_display()}'
