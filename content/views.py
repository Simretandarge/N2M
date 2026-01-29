"""
Views for Next 251 Media: home, articles, category hubs, reviews, about, contact, legal.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from .models import Category, Post, Review
from .forms import ContactForm, NewsletterForm


def _published_posts():
    return Post.objects.filter(
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    ).select_related('category')


def _published_reviews():
    return Review.objects.filter(
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )


def home(request):
    """Home: hero, featured post, latest grid, topic links, trending, newsletter."""
    posts = _published_posts()
    featured = posts.filter(is_featured=True).first()
    if not featured:
        featured = posts.first()
    latest = posts.exclude(pk=featured.pk if featured else None)[:9]
    trending = posts.order_by('-views')[:5]
    return render(request, 'content/home.html', {
        'featured': featured,
        'latest': latest,
        'trending': trending,
    })


def post_list(request):
    """Articles list with category filter, search, pagination."""
    posts = _published_posts()
    q = request.GET.get('q', '').strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(content__icontains=q) | Q(excerpt__icontains=q))
    cat_slug = request.GET.get('category', '')
    if cat_slug:
        posts = posts.filter(category__slug=cat_slug)
    paginator = Paginator(posts, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    return render(request, 'content/post_list.html', {
        'page_obj': page_obj,
        'q': q,
        'category_slug': cat_slug,
        'categories': Category.objects.all().order_by('name'),
    })


def post_detail(request, slug):
    """Post detail; increment view count."""
    post = get_object_or_404(
        Post.objects.select_related('category'),
        slug=slug,
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )
    post.views += 1
    post.save(update_fields=['views'])
    related = _published_posts().filter(category=post.category).exclude(pk=post.pk)[:4]
    return render(request, 'content/post_detail.html', {'post': post, 'related': related})


def category_detail(request, slug):
    """Topic hub (AI, Startups): featured + latest for that category."""
    category = get_object_or_404(Category, slug=slug)
    posts = _published_posts().filter(category=category)
    featured = posts.filter(is_featured=True).first() or posts.first()
    latest = posts.exclude(pk=featured.pk if featured else None)[:12]
    return render(request, 'content/category_detail.html', {
        'category': category,
        'featured': featured,
        'latest': latest,
    })


def review_list(request):
    """Reviews list with pagination."""
    reviews = _published_reviews()
    paginator = Paginator(reviews, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    return render(request, 'content/review_list.html', {'page_obj': page_obj})


def review_detail(request, slug):
    """Review detail page."""
    review = get_object_or_404(
        Review,
        slug=slug,
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )
    return render(request, 'content/review_detail.html', {'review': review})


def about(request):
    """About: what N2M is, mission, what we cover, meaning of 251."""
    return render(request, 'content/about.html')


def contact(request):
    """Contact form + email/social links."""
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # Placeholder: in production, send email or save to DB
        messages.success(request, 'Thank you. We will get back to you soon.')
        return redirect('content:contact')
    return render(request, 'content/contact.html', {'form': form})


def newsletter_signup(request):
    """Newsletter signup (POST from home/footer)."""
    if request.method != 'POST':
        return redirect('content:home')
    form = NewsletterForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'You have been subscribed. Thank you.')
    else:
        messages.warning(request, 'Please enter a valid email or you may already be subscribed.')
    referrer = request.META.get('HTTP_REFERER') or reverse('content:home')
    return redirect(referrer)


def privacy(request):
    """Privacy Policy."""
    return render(request, 'content/privacy.html')


def terms(request):
    """Terms of Service."""
    return render(request, 'content/terms.html')


def robots_txt(request):
    """Serve robots.txt with sitemap link."""
    from django.http import HttpResponse
    from django.urls import reverse
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Sitemap: {request.build_absolute_uri(reverse("sitemap"))}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')
