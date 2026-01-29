"""
Sitemaps for SEO: posts, reviews, static pages.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Post, Review


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Post.objects.filter(status='published', published_at__isnull=False)

    def lastmod(self, obj):
        return obj.updated_at


class ReviewSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Review.objects.filter(status='published', published_at__isnull=False)

    def lastmod(self, obj):
        return obj.updated_at


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return ['content:home', 'content:post_list', 'content:category_ai', 'content:category_startups',
                'content:review_list', 'content:about', 'content:contact', 'content:privacy', 'content:terms']

    def location(self, item):
        return reverse(item)
