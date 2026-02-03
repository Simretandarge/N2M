"""
Views for Next 251 Media: home, articles, category hubs, reviews, about, contact, legal.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Category, Post, Review
from .forms import ContactForm, NewsletterForm, PostForm, ReviewForm


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
    """Home: only published/approved content. Featured post, latest articles, latest reviews, topics, trending, newsletter."""
    posts = _published_posts()
    featured = posts.filter(is_featured=True).first()
    if not featured:
        featured = posts.first()
    latest = list(posts.exclude(pk=featured.pk if featured else None)[:9])
    trending = list(posts.order_by('-views')[:5])
    latest_reviews = list(_published_reviews()[:6])
    return render(request, 'content/home.html', {
        'featured': featured,
        'latest': latest,
        'trending': trending,
        'latest_reviews': latest_reviews,
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
    share_url = request.build_absolute_uri(post.get_absolute_url())
    return render(request, 'content/post_detail.html', {
        'post': post, 'related': related, 'share_url': share_url,
    })


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
    share_url = request.build_absolute_uri(review.get_absolute_url())
    return render(request, 'content/review_detail.html', {'review': review, 'share_url': share_url})


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


# ----- Writer interface (no Django admin) -----

def _user_is_writer(user):
    """User is in Writers group (can use writer post interface)."""
    return user.is_authenticated and user.groups.filter(name='Writers').exists()


def _writer_redirect(request):
    """Redirect non-writers away from writer views."""
    from django.urls import reverse as rev
    if request.user.is_superuser:
        return redirect(rev('accounts:dashboard_admin'))
    if request.user.groups.filter(name='Editors').exists():
        return redirect(rev('accounts:dashboard_editor'))
    return redirect(rev('accounts:login'))


@login_required
def writer_post_list(request):
    """List posts by the current user (writers only)."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    posts = Post.objects.filter(author=request.user).select_related('category').order_by('-updated_at')
    paginator = Paginator(posts, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'content/writer/post_list.html', {'page_obj': page_obj})


@login_required
def writer_post_create(request):
    """Create a new post (writers only). New posts are always draft."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = 'draft'
            post.is_featured = False
            post.save()
            messages.success(request, 'Post saved as draft.')
            return redirect('content:writer_post_edit', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'content/writer/post_form.html', {'form': form, 'post': None})


@login_required
def writer_post_edit(request, pk):
    """Edit own post (writers only). Writers cannot set status to published."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user:
        messages.error(request, 'You can only edit your own posts.')
        return redirect('content:writer_post_list')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # Keep status as draft for writers (they cannot publish)
            post = form.save(commit=False)
            post.author = request.user
            if post.status != 'published':
                post.status = 'draft'
            post.save()
            messages.success(request, 'Post updated.')
            return redirect('content:writer_post_list')
    else:
        form = PostForm(instance=post)
    return render(request, 'content/writer/post_form.html', {'form': form, 'post': post})


@login_required
def writer_review_list(request):
    """List reviews by the current user (writers only)."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    reviews = Review.objects.filter(author=request.user).order_by('-updated_at')
    paginator = Paginator(reviews, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'content/writer/review_list.html', {'page_obj': page_obj})


@login_required
def writer_review_create(request):
    """Create a new review (writers only). New reviews are always draft."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            review.status = 'draft'
            review.save()
            messages.success(request, 'Review saved as draft.')
            return redirect('content:writer_review_edit', pk=review.pk)
    else:
        form = ReviewForm()
    return render(request, 'content/writer/review_form.html', {'form': form, 'review': None})


@login_required
def writer_review_edit(request, pk):
    """Edit own review (writers only). Writers cannot set status to published."""
    if not _user_is_writer(request.user):
        return _writer_redirect(request)
    review = get_object_or_404(Review, pk=pk)
    if review.author != request.user:
        messages.error(request, 'You can only edit your own reviews.')
        return redirect('content:writer_review_list')
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.author = request.user
            if review.status != 'published':
                review.status = 'draft'
            review.save()
            messages.success(request, 'Review updated.')
            return redirect('content:writer_review_list')
    else:
        form = ReviewForm(instance=review)
    return render(request, 'content/writer/review_form.html', {'form': form, 'review': review})
