"""
Load sample categories and posts so you can see cards on the home and articles pages.
Run: python manage.py load_sample_content
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from content.models import Category, Post, Review


class Command(BaseCommand):
    help = 'Create sample categories (AI, Startups) and published posts so cards appear on the site.'

    def handle(self, *args, **options):
        # Categories
        ai, _ = Category.objects.get_or_create(slug='ai', defaults={'name': 'AI'})
        technology, _ = Category.objects.get_or_create(slug='technology', defaults={'name': 'Technology'})
        business, _ = Category.objects.get_or_create(slug='business', defaults={'name': 'Business'})
        startups, _ = Category.objects.get_or_create(slug='startups', defaults={'name': 'Startups'})
        innovation, _ = Category.objects.get_or_create(slug='innovation', defaults={'name': 'Innovation'})
        self.stdout.write('Categories: Technology, AI, Business, Startups, Innovation')

        # Sample posts (only create if none exist)
        if Post.objects.filter(status='published').exists():
            self.stdout.write(self.style.WARNING('Published posts already exist. Skipping posts.'))
        else:
            sample_posts = [
                {
                    'title': 'What is AI? A short explainer',
                    'slug': 'what-is-ai-explainer',
                    'excerpt': 'A calm, clear introduction to artificial intelligence and why it matters for Africa and the world.',
                    'content': 'Artificial intelligence (AI) refers to systems that can perform tasks that usually require human intelligence: understanding language, recognizing images, making decisions. This post is sample content so you can see how article cards look on the site. Add your own posts via the admin.',
                    'category': ai,
                    'is_featured': True,
                    'status': 'published',
                    'published_at': timezone.now(),
                },
                {
                    'title': 'Building your first MVP',
                    'slug': 'building-first-mvp',
                    'excerpt': 'How to validate an idea and ship a minimum viable product without burning out.',
                    'content': 'An MVP is the smallest version of your product that delivers value and lets you learn from real users. Focus on one problem, one solution, and get it in front of people fast. This is sample content for the N2M site.',
                    'category': startups,
                    'is_featured': False,
                    'status': 'published',
                    'published_at': timezone.now(),
                },
                {
                    'title': 'AI tools for startups in 2025',
                    'slug': 'ai-tools-for-startups-2025',
                    'excerpt': 'A roundup of AI tools that can help founders save time and focus on growth.',
                    'content': 'From writing and design to code and analytics, AI tools are becoming essential for lean teams. Here we share a few categories and ideas—replace this with your own analysis and reviews.',
                    'category': ai,
                    'is_featured': False,
                    'status': 'published',
                    'published_at': timezone.now(),
                },
                {
                    'title': 'Why Africa’s tech ecosystem matters',
                    'slug': 'why-africa-tech-ecosystem-matters',
                    'excerpt': 'The rise of innovation hubs, talent, and capital across the continent.',
                    'content': 'Africa’s tech scene is growing fast: more startups, more funding, and more focus on local problems. This sample post is a placeholder for your own take on the ecosystem.',
                    'category': startups,
                    'is_featured': False,
                    'status': 'published',
                    'published_at': timezone.now(),
                },
            ]
            for data in sample_posts:
                Post.objects.get_or_create(slug=data['slug'], defaults=data)
            self.stdout.write(self.style.SUCCESS(f'Created {len(sample_posts)} sample posts.'))

        # One sample review
        if Review.objects.filter(status='published').exists():
            self.stdout.write(self.style.WARNING('Published reviews already exist. Skipping reviews.'))
        else:
            Review.objects.get_or_create(
                slug='sample-tool-review',
                defaults={
                    'title': 'Sample tool review',
                    'product_name': 'Sample Product',
                    'summary': 'A short sample review so you can see how review cards look.',
                    'content': 'This is placeholder content for a product or tool review. Add your own reviews in the admin with pros, cons, and a verdict.',
                    'rating': 4,
                    'pros': 'Easy to use, Good value',
                    'cons': 'Limited integrations',
                    'status': 'published',
                    'published_at': timezone.now(),
                }
            )
            self.stdout.write(self.style.SUCCESS('Created 1 sample review.'))

        self.stdout.write(self.style.SUCCESS('Done. Refresh http://127.0.0.1:8000/ to see the cards.'))
