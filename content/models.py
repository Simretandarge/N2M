"""
Content models for Next 251 Media (N2M).
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse


class Category(models.Model):
    """Topic/category for posts (e.g. AI, Startups)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from .departments import category_hub_url
        return category_hub_url(self.slug)


class Post(models.Model):
    """Article/post with draft/publish workflow and featured support."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    excerpt = models.TextField(blank=True)
    content = models.TextField()
    instagram_post_url = models.URLField(
        max_length=500,
        blank=True,
        help_text='Optional. Permalink to this story on @next251media (e.g. https://www.instagram.com/p/… or /reel/…). Used by the site “Share → Instagram” action.',
    )
    featured_image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, null=True)
    featured_video = models.FileField(upload_to='posts/videos/%Y/%m/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_posts',
    )
    is_featured = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_posts',
        help_text='User who published this (editor or admin).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            self.slug = base
            n = 1
            while Post.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base}-{n}'
                n += 1
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('content:post_detail', kwargs={'slug': self.slug})

    @property
    def published(self):
        return self.status == 'published' and (
            self.published_at is None or self.published_at <= timezone.now()
        )


class PostLike(models.Model):
    """User likes on a post (one like per user per post)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_likes',
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'post']]

    def __str__(self):
        return f'{self.user.get_username()} likes {self.post.title}'


class PostComment(models.Model):
    """Comment on a post."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_comments',
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.get_username()} on {self.post.title}'


class Review(models.Model):
    """Product/service review with optional rating, pros/cons."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    product_name = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    content = models.TextField()
    instagram_post_url = models.URLField(
        max_length=500,
        blank=True,
        help_text='Optional. Permalink to this review on @next251media (Instagram post or reel URL).',
    )
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # e.g. 1-5
    pros = models.TextField(blank=True, help_text='One pro per line or comma-separated')
    cons = models.TextField(blank=True, help_text='One con per line or comma-separated')
    featured_image = models.ImageField(upload_to='reviews/%Y/%m/', blank=True, null=True)
    featured_video = models.FileField(upload_to='reviews/videos/%Y/%m/', blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_reviews',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='published_reviews',
        help_text='User who published this (editor or admin).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            self.slug = base
            n = 1
            while Review.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f'{base}-{n}'
                n += 1
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('content:review_detail', kwargs={'slug': self.slug})

    @property
    def published(self):
        return self.status == 'published' and (
            self.published_at is None or self.published_at <= timezone.now()
        )

    def pros_list(self):
        return [s.strip() for s in (self.pros or '').replace(',', '\n').splitlines() if s.strip()]

    def cons_list(self):
        return [s.strip() for s in (self.cons or '').replace(',', '\n').splitlines() if s.strip()]


class ReviewLike(models.Model):
    """User like on a review (one like per user per review)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_likes',
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'review']]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.get_username()} likes {self.review.title}'


class ReviewComment(models.Model):
    """Comment on a review."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_comments',
    )
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.get_username()} on {self.review.title}'


class NewsletterSubscriber(models.Model):
    """Newsletter signup: weekly digest only."""
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_CHOICES = [
        (FREQUENCY_WEEKLY, 'Weekly'),
    ]
    email = models.EmailField(unique=True)
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_WEEKLY,
        help_text='Send digest weekly (last 7 days).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} ({self.frequency})'


class NewsletterIssueManager(models.Manager):
    """Avoid selecting `views` when that column is missing (code deployed before migrate)."""

    def get_queryset(self):
        qs = super().get_queryset()
        from content.db_compat import newsletter_issue_has_views_column
        if not newsletter_issue_has_views_column():
            qs = qs.defer('views')
        return qs


class NewsletterIssue(models.Model):
    """A newsletter issue that can be drafted, posted on site, and/or sent by email."""
    objects = NewsletterIssueManager()
    STATUS_DRAFT = 'draft'
    STATUS_POSTED = 'posted'
    STATUS_SENT = 'sent'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_POSTED, 'Posted'),
        (STATUS_SENT, 'Sent'),
    ]
    title = models.CharField(max_length=255)
    content = models.TextField(help_text='Plain text or HTML body of the newsletter.')
    hero_image = models.ImageField(upload_to='newsletters/%Y/%m/', blank=True, null=True)
    hero_video = models.FileField(upload_to='newsletters/videos/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    posted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this was posted on the site; null = not posted yet.',
    )
    sent_at = models.DateTimeField(null=True, blank=True, help_text='When this was sent; null = draft.')
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_newsletter_issues',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} — {self.get_status_display()}'

    @property
    def is_sent(self):
        return self.status == self.STATUS_SENT

    @property
    def is_posted(self):
        return self.status in {self.STATUS_POSTED, self.STATUS_SENT}

    def get_absolute_url(self):
        return reverse('content:newsletter_issue_detail', kwargs={'pk': self.pk})


class NewsletterIssueLike(models.Model):
    """User like on a newsletter issue (one like per user per issue)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='newsletter_issue_likes',
    )
    issue = models.ForeignKey(
        NewsletterIssue,
        on_delete=models.CASCADE,
        related_name='likes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'issue']]

    def __str__(self):
        return f'{self.user.get_username()} likes {self.issue.title}'


class PostMedia(models.Model):
    """Additional post media items (up to 6 images and 6 videos per post)."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media_items')
    image = models.ImageField(upload_to='posts/gallery/%Y/%m/', blank=True, null=True)
    video = models.FileField(upload_to='posts/videos/gallery/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Post media for {self.post.title}'


class ReviewMedia(models.Model):
    """Additional review media items (up to 6 images and 6 videos per review)."""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='media_items')
    image = models.ImageField(upload_to='reviews/gallery/%Y/%m/', blank=True, null=True)
    video = models.FileField(upload_to='reviews/videos/gallery/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Review media for {self.review.title}'


class NewsletterIssueMedia(models.Model):
    """Additional newsletter media items (up to 6 images and 6 videos per issue)."""
    issue = models.ForeignKey(NewsletterIssue, on_delete=models.CASCADE, related_name='media_items')
    image = models.ImageField(upload_to='newsletters/gallery/%Y/%m/', blank=True, null=True)
    video = models.FileField(upload_to='newsletters/videos/gallery/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Newsletter media for {self.issue.title}'
