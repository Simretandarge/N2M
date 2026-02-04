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
        return reverse('content:category_detail', kwargs={'slug': self.slug})


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
    featured_image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, null=True)
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
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # e.g. 1-5
    pros = models.TextField(blank=True, help_text='One pro per line or comma-separated')
    cons = models.TextField(blank=True, help_text='One con per line or comma-separated')
    featured_image = models.ImageField(upload_to='reviews/%Y/%m/', blank=True, null=True)
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


class NewsletterSubscriber(models.Model):
    """Newsletter signup (email only)."""
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email
