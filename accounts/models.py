"""
Account-related models: editor applications, reader bookmarks, reader preferences.
"""
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Additional user profile fields (e.g. profile photo)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile_ext',
    )
    photo = models.ImageField(upload_to='profiles/%Y/%m/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user.get_username()}'


class BookmarkedPost(models.Model):
    """Reader bookmarks: save articles for later."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarked_posts',
    )
    post = models.ForeignKey(
        'content.Post',
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'post']]

    def __str__(self):
        return f'{self.user.get_username()} — {self.post.title}'


class BookmarkedReview(models.Model):
    """Reader bookmarks: save reviews for later."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarked_reviews',
    )
    review = models.ForeignKey(
        'content.Review',
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'review']]

    def __str__(self):
        return f'{self.user.get_username()} — {self.review.title}'


class BookmarkedNewsletterIssue(models.Model):
    """Reader bookmarks: save newsletter issues for later."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarked_newsletter_issues',
    )
    newsletter_issue = models.ForeignKey(
        'content.NewsletterIssue',
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'newsletter_issue']]

    def __str__(self):
        return f'{self.user.get_username()} — {self.newsletter_issue.title}'


class ReaderPreference(models.Model):
    """Reader topic and newsletter preferences (AI, Startups, Reviews, weekly insights)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reader_preference',
    )
    follow_ai = models.BooleanField(default=True, help_text='Follow AI topic')
    follow_startups = models.BooleanField(default=True, help_text='Follow Startups topic')
    follow_reviews = models.BooleanField(default=True, help_text='Follow Reviews')
    newsletter_weekly = models.BooleanField(
        default=True,
        help_text='Receive weekly insights newsletter',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Preferences for {self.user.get_username()}'


class WriterApplication(models.Model):
    """Reader's request to become a writer. Admins approve or reject."""
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
        related_name='writer_applications',
    )
    message = models.TextField(
        blank=True,
        help_text='Why you want to become a writer (optional).',
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
        related_name='reviewed_writer_applications',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_username()} — {self.get_status_display()}'


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
