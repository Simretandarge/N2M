"""
Views for Next 251 Media: home, articles, category hubs, reviews, about, contact, legal.
"""
import hashlib
import logging
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import (
    Category,
    Post,
    PostLike,
    PostComment,
    Review,
    ReviewLike,
    ReviewComment,
    NewsletterIssue,
    NewsletterSubscriber,
    NewsletterIssueLike,
    PostMedia,
    ReviewMedia,
    NewsletterIssueMedia,
)
from accounts.models import BookmarkedPost, BookmarkedReview, BookmarkedNewsletterIssue
from .db_compat import newsletter_issue_has_views_column
from django.core.mail import send_mail, get_connection, EmailMessage
from django.template.loader import render_to_string
from datetime import timedelta
from zoneinfo import ZoneInfo

from .departments import DEPARTMENT_ORDER, DEPARTMENT_BLURBS
from .forms import (
    ContactForm,
    NewsletterForm,
    PostCommentForm,
    ReviewCommentForm,
    PostForm,
    ReviewForm,
    PostFormEditor,
    ReviewFormEditor,
    CategoryForm,
    NewsletterIssueForm,
)

logger = logging.getLogger(__name__)


def _public_count_salt() -> str:
    extra = getattr(settings, 'DISPLAY_COUNT_SALT', '') or ''
    secret = getattr(settings, 'SECRET_KEY', '') or ''
    return f'{extra}:{secret[:48]}'


def _stable_range(seed: str, min_v: int, max_v: int) -> int:
    if max_v < min_v:
        min_v, max_v = max_v, min_v
    if max_v == min_v:
        return min_v
    h = hashlib.sha256(seed.encode('utf-8')).digest()
    n = int.from_bytes(h[:4], 'big')
    return min_v + (n % (max_v - min_v + 1))


def _public_count_boost(seed: str, min_v: int, max_v: int) -> int:
    if not getattr(settings, 'DISPLAY_COUNT_BOOST_ENABLED', True):
        return 0
    return _stable_range(seed, min_v, max_v)


def publication_time_for_boost(obj, kind: str):
    """When boosted public counts should start counting from."""
    if kind == 'newsletter':
        return (
            getattr(obj, 'posted_at', None)
            or getattr(obj, 'sent_at', None)
            or getattr(obj, 'created_at', None)
        )
    return getattr(obj, 'published_at', None) or getattr(obj, 'created_at', None)


def _display_count_boost_allowed(published_at, pk: int, kind: str) -> bool:
    """False until a stable delay after publish/post has elapsed."""
    if not getattr(settings, 'DISPLAY_COUNT_BOOST_ENABLED', True):
        return False
    delay_lo = int(getattr(settings, 'DISPLAY_COUNT_BOOST_DELAY_MIN_MINUTES', 30))
    delay_hi = int(getattr(settings, 'DISPLAY_COUNT_BOOST_DELAY_MAX_MINUTES', 60))
    if delay_lo <= 0 and delay_hi <= 0:
        return True
    if published_at is None:
        return True
    delay_minutes = _stable_range(
        f'delay:{kind}:{pk}:{_public_count_salt()}',
        delay_lo,
        delay_hi,
    )
    if timezone.is_naive(published_at):
        published_at = timezone.make_aware(published_at)
    return timezone.now() >= published_at + timedelta(minutes=delay_minutes)


def display_like_public(real: int, pk: int, kind: str, published_at=None) -> int:
    """Public-facing like total; kind is 'post' | 'review' | 'newsletter'."""
    real = max(0, int(real))
    if not _display_count_boost_allowed(published_at, pk, kind):
        return real
    lo = int(getattr(settings, 'DISPLAY_LIKE_BOOST_MIN', 15))
    hi = int(getattr(settings, 'DISPLAY_LIKE_BOOST_MAX', 45))
    b = _public_count_boost(f'like:{kind}:{pk}:{_public_count_salt()}', lo, hi)
    return real + b


def display_save_public(real: int, pk: int, kind: str, published_at=None) -> int:
    real = max(0, int(real))
    if not _display_count_boost_allowed(published_at, pk, kind):
        return real
    lo = int(getattr(settings, 'DISPLAY_SAVE_BOOST_MIN', 3))
    hi = int(getattr(settings, 'DISPLAY_SAVE_BOOST_MAX', 6))
    b = _public_count_boost(f'save:{kind}:{pk}:{_public_count_salt()}', lo, hi)
    return real + b


def display_view_public(
    real_views: int,
    real_likes: int,
    pk: int,
    kind: str,
    published_at=None,
) -> int:
    """
    Public-facing view total: real views + stable bump, never below (public likes + stable gap).
    Keeps “views” plausible when like/save counts are boosted.
    """
    real_views = max(0, int(real_views))
    real_likes = max(0, int(real_likes))
    if not _display_count_boost_allowed(published_at, pk, kind):
        return real_views
    like_pub = display_like_public(real_likes, pk, kind, published_at)
    v_lo = int(getattr(settings, 'DISPLAY_VIEW_BOOST_MIN', 22))
    v_hi = int(getattr(settings, 'DISPLAY_VIEW_BOOST_MAX', 72))
    view_b = _public_count_boost(f'view:{kind}:{pk}:{_public_count_salt()}', v_lo, v_hi)
    base = real_views + view_b
    gap_lo = int(getattr(settings, 'DISPLAY_VIEW_OVER_LIKE_MIN', 12))
    gap_hi = int(getattr(settings, 'DISPLAY_VIEW_OVER_LIKE_MAX', 52))
    gap = _public_count_boost(f'viewoverlike:{kind}:{pk}:{_public_count_salt()}', gap_lo, gap_hi)
    floor = like_pub + gap
    return max(base, floor)


def _inline_toggle_ajax(request):
    """True when frontend wants JSON (no redirect)."""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('ajax') == '1'
    )


def _validate_extra_media_limits(form, instance, media_model, parent_field):
    """Validate total cap: up to 6 images and 6 videos per object."""
    images = form.files.getlist('extra_images')
    videos = form.files.getlist('extra_videos')
    existing_images = 0
    existing_videos = 0
    if getattr(instance, 'pk', None):
        existing_images = media_model.objects.filter(**{parent_field: instance}, image__isnull=False).count()
        existing_videos = media_model.objects.filter(**{parent_field: instance}, video__isnull=False).count()
    ok = True
    if existing_images + len(images) > 6:
        form.add_error('extra_images', f'You can store up to 6 images total. Already stored: {existing_images}.')
        ok = False
    if existing_videos + len(videos) > 6:
        form.add_error('extra_videos', f'You can store up to 6 videos total. Already stored: {existing_videos}.')
        ok = False
    return ok, images, videos


def _save_extra_media_items(instance, images, videos, media_model, parent_field):
    """Persist extra uploaded media files."""
    for f in images:
        media_model.objects.create(**{parent_field: instance, 'image': f})
    for f in videos:
        media_model.objects.create(**{parent_field: instance, 'video': f})


def _newsletter_issue_has_views_field():
    """True when the database has a views column for NewsletterIssue (migration applied)."""
    return newsletter_issue_has_views_column()


def _published_posts():
    return Post.objects.filter(
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    ).select_related('category').prefetch_related('media_items')


def _published_reviews():
    return Review.objects.filter(
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    ).prefetch_related('media_items')


def home(request):
    """Home: editorial hero, featured story, department hubs, trending, and newsletter."""
    posts = _published_posts().annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
        bookmark_count=Count('bookmarked_by', distinct=True),
        gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
        sort_date=Coalesce('published_at', 'created_at'),
    ).order_by('-sort_date', '-pk')
    featured = posts.filter(is_featured=True).order_by('-published_at', '-created_at').first()
    if not featured:
        featured = posts.first()

    shown_pks = set()
    if featured:
        shown_pks.add(featured.pk)
    featured_secondary = list(posts.exclude(pk__in=shown_pks)[:3])
    shown_pks.update(p.pk for p in featured_secondary)
    latest = list(posts.exclude(pk__in=shown_pks)[:9])

    trending = list(posts.order_by('-views')[:3])
    latest_reviews = list(
        _published_reviews().annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
            gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
            sort_date=Coalesce('published_at', 'created_at'),
        ).order_by('-sort_date', '-pk')[:6]
    )
    newsletter_home_qs = (
        NewsletterIssue.objects.filter(
            status__in=[NewsletterIssue.STATUS_POSTED, NewsletterIssue.STATUS_SENT],
        )
        .prefetch_related('media_items')
        .annotate(
            gallery_image_count=Count(
                'media_items',
                filter=Q(media_items__image__isnull=False),
                distinct=True,
            ),
            like_count=Count('likes', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
            sort_date=Coalesce('sent_at', 'posted_at', 'created_at'),
        )
    )
    latest_newsletters = list(
        newsletter_home_qs.order_by('-sort_date', '-pk')[:6]
    )
    newsletter_show_view_counts = _newsletter_issue_has_views_field()
    if newsletter_show_view_counts:
        try:
            trending_newsletters = list(
                newsletter_home_qs.order_by('-views', '-like_count', '-sent_at', '-posted_at')[:5]
            )
        except Exception:
            newsletter_show_view_counts = False
            trending_newsletters = list(
                newsletter_home_qs.order_by('-like_count', '-sent_at', '-posted_at', '-created_at')[:5]
            )
    else:
        trending_newsletters = list(
            newsletter_home_qs.order_by('-like_count', '-sent_at', '-posted_at', '-created_at')[:5]
        )
    liked_post_ids = set()
    bookmarked_post_ids = set()
    liked_review_ids = set()
    bookmarked_review_ids = set()
    liked_newsletter_ids = set()
    saved_newsletter_ids = set()
    if request.user.is_authenticated:
        liked_post_ids = set(PostLike.objects.filter(user=request.user).values_list('post_id', flat=True))
        bookmarked_post_ids = set(BookmarkedPost.objects.filter(user=request.user).values_list('post_id', flat=True))
        liked_review_ids = set(ReviewLike.objects.filter(user=request.user).values_list('review_id', flat=True))
        bookmarked_review_ids = set(
            BookmarkedReview.objects.filter(user=request.user).values_list('review_id', flat=True)
        )
        liked_newsletter_ids = set(
            NewsletterIssueLike.objects.filter(user=request.user).values_list('issue_id', flat=True)
        )
        saved_newsletter_ids = set(
            BookmarkedNewsletterIssue.objects.filter(user=request.user).values_list(
                'newsletter_issue_id', flat=True
            )
        )

    latest_stories_fallback = False
    if not latest and latest_newsletters:
        latest = latest_newsletters[:6]
        latest_stories_fallback = True

    cats_by_slug = {c.slug: c for c in Category.objects.filter(slug__in=DEPARTMENT_ORDER)}
    departments = []
    for slug in DEPARTMENT_ORDER:
        category = cats_by_slug.get(slug)
        if not category:
            continue
        dept_posts = list(
            posts.filter(category=category).exclude(pk__in=shown_pks)[:3]
        )
        departments.append({
            'category': category,
            'blurb': DEPARTMENT_BLURBS.get(slug, ''),
            'posts': dept_posts,
        })

    context = {
        'featured': featured,
        'featured_secondary': featured_secondary,
        'latest': latest,
        'latest_stories_fallback': latest_stories_fallback,
        'departments': departments,
        'trending': trending,
        'latest_reviews': latest_reviews,
        'latest_newsletters': latest_newsletters,
        'trending_newsletters': trending_newsletters,
        'liked_post_ids': liked_post_ids,
        'bookmarked_post_ids': bookmarked_post_ids,
        'liked_review_ids': liked_review_ids,
        'bookmarked_review_ids': bookmarked_review_ids,
        'liked_newsletter_ids': liked_newsletter_ids,
        'saved_newsletter_ids': saved_newsletter_ids,
        'newsletter_show_view_counts': newsletter_show_view_counts,
    }
    # Reader dashboard on home: show when logged in as reader (no Editors/Writers group, not superuser)
    if request.user.is_authenticated and not request.user.is_superuser and not request.user.groups.filter(name='Editors').exists() and not request.user.groups.filter(name='Writers').exists():
        context['reader_bookmarks_count'] = (
            BookmarkedPost.objects.filter(user=request.user).count()
            + BookmarkedReview.objects.filter(user=request.user).count()
            + BookmarkedNewsletterIssue.objects.filter(user=request.user).count()
        )
    return render(request, 'content/home.html', context)


def post_list(request):
    """Articles list with category filter, search (all categories + by category name), pagination."""
    posts = _published_posts().annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
        bookmark_count=Count('bookmarked_by', distinct=True),
        gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
    ).order_by('-published_at', '-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        # Search in title, excerpt, content, and category name (so "AI" or "Startups" finds that category's posts)
        posts = posts.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(excerpt__icontains=q) | Q(category__name__icontains=q)
        )
    cat_slug = request.GET.get('category', '')
    if cat_slug:
        posts = posts.filter(category__slug=cat_slug)
    liked_post_ids = set()
    bookmarked_post_ids = set()
    if request.user.is_authenticated:
        liked_post_ids = set(PostLike.objects.filter(user=request.user).values_list('post_id', flat=True))
        bookmarked_post_ids = set(BookmarkedPost.objects.filter(user=request.user).values_list('post_id', flat=True))
    paginator = Paginator(posts, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    return render(request, 'content/post_list.html', {
        'page_obj': page_obj,
        'q': q,
        'category_slug': cat_slug,
        'categories': Category.objects.all().order_by('name'),
        'liked_post_ids': liked_post_ids,
        'bookmarked_post_ids': bookmarked_post_ids,
    })


def post_detail(request, slug):
    """Post detail; increment view count. Pass like/save state (comments disabled)."""
    post = get_object_or_404(
        Post.objects.select_related('category').annotate(
            like_count=Count('likes', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
        ),
        slug=slug,
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )
    post.views += 1
    post.save(update_fields=['views'])
    related = _published_posts().filter(category=post.category).exclude(pk=post.pk)[:4]
    share_url = request.build_absolute_uri(post.get_absolute_url())
    is_bookmarked = (
        request.user.is_authenticated and
        BookmarkedPost.objects.filter(user=request.user, post=post).exists()
    )
    is_liked = (
        request.user.is_authenticated and
        post.likes.filter(user=request.user).exists()
    )
    public_like_count = display_like_public(
        post.like_count, post.pk, 'post', publication_time_for_boost(post, 'post'),
    )
    public_save_count = display_save_public(
        post.bookmark_count, post.pk, 'post', publication_time_for_boost(post, 'post'),
    )
    return render(request, 'content/post_detail.html', {
        'post': post,
        'related': related,
        'share_url': share_url,
        'is_bookmarked': is_bookmarked,
        'is_liked': is_liked,
        'public_like_count': public_like_count,
        'public_save_count': public_save_count,
        # comments disabled on article detail
        'comments': [],
        'comment_form': None,
    })


@login_required
def post_like_toggle(request, slug):
    """Toggle like on a post; redirect back to post."""
    post = get_object_or_404(
        Post.objects.filter(
            status='published',
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        ),
        slug=slug,
    )
    like = post.likes.filter(user=request.user).first()
    if like:
        like.delete()
    else:
        PostLike.objects.get_or_create(user=request.user, post=post)
    if _inline_toggle_ajax(request):
        like_count = display_like_public(
            post.likes.count(), post.pk, 'post', publication_time_for_boost(post, 'post'),
        )
        liked = post.likes.filter(user=request.user).exists()
        return JsonResponse({'ok': True, 'liked': liked, 'like_count': like_count})
    next_url = request.GET.get('next') or request.POST.get('next') or post.get_absolute_url()
    return redirect(next_url)


def category_detail(request, slug):
    """Topic hub (AI, Startups): featured + latest for that category."""
    category = get_object_or_404(Category, slug=slug)
    posts = _published_posts().filter(category=category).annotate(
        gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
    )
    featured = posts.filter(is_featured=True).first() or posts.first()
    latest = posts.exclude(pk=featured.pk if featured else None)[:12]
    return render(request, 'content/category_detail.html', {
        'category': category,
        'featured': featured,
        'latest': latest,
    })


def review_list(request):
    """Reviews list with search, optional rating filter, and pagination."""
    reviews = _published_reviews().annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', distinct=True),
        bookmark_count=Count('bookmarked_by', distinct=True),
        gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
    ).order_by('-published_at', '-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        reviews = reviews.filter(
            Q(title__icontains=q) | Q(product_name__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q)
        )
    rating_filter = request.GET.get('rating', '')
    if rating_filter and rating_filter.isdigit():
        min_rating = int(rating_filter)
        if 1 <= min_rating <= 5:
            reviews = reviews.filter(rating__gte=min_rating)
    bookmarked_review_ids = set()
    liked_review_ids = set()
    if request.user.is_authenticated:
        bookmarked_review_ids = set(BookmarkedReview.objects.filter(user=request.user).values_list('review_id', flat=True))
        liked_review_ids = set(ReviewLike.objects.filter(user=request.user).values_list('review_id', flat=True))
    paginator = Paginator(reviews, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    return render(request, 'content/review_list.html', {
        'page_obj': page_obj,
        'q': q,
        'rating_filter': rating_filter,
        'bookmarked_review_ids': bookmarked_review_ids,
        'liked_review_ids': liked_review_ids,
    })


def review_detail(request, slug):
    """Review detail page (comments disabled)."""
    review = get_object_or_404(
        Review.objects.annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
        ),
        slug=slug,
        status='published',
        published_at__isnull=False,
        published_at__lte=timezone.now(),
    )
    share_url = request.build_absolute_uri(review.get_absolute_url())
    is_bookmarked = (
        request.user.is_authenticated and
        BookmarkedReview.objects.filter(user=request.user, review=review).exists()
    )
    is_liked = (
        request.user.is_authenticated and
        ReviewLike.objects.filter(user=request.user, review=review).exists()
    )
    public_like_count = display_like_public(
        review.like_count, review.pk, 'review', publication_time_for_boost(review, 'review'),
    )
    public_save_count = display_save_public(
        review.bookmark_count, review.pk, 'review', publication_time_for_boost(review, 'review'),
    )
    return render(request, 'content/review_detail.html', {
        'review': review,
        'share_url': share_url,
        'is_bookmarked': is_bookmarked,
        'is_liked': is_liked,
        'public_like_count': public_like_count,
        'public_save_count': public_save_count,
        # comments disabled on review detail
        'comments': [],
        'comment_form': None,
    })


@login_required
def review_like_toggle(request, slug):
    """Toggle like on a review; redirect back to review."""
    review = get_object_or_404(
        Review.objects.filter(
            status='published',
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        ),
        slug=slug,
    )
    like = ReviewLike.objects.filter(user=request.user, review=review).first()
    if like:
        like.delete()
    else:
        ReviewLike.objects.get_or_create(user=request.user, review=review)
    if _inline_toggle_ajax(request):
        like_count = display_like_public(
            review.likes.count(), review.pk, 'review', publication_time_for_boost(review, 'review'),
        )
        liked = ReviewLike.objects.filter(user=request.user, review=review).exists()
        return JsonResponse({'ok': True, 'liked': liked, 'like_count': like_count})
    next_url = request.GET.get('next') or request.POST.get('next') or review.get_absolute_url()
    return redirect(next_url)


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
    """Newsletter signup (POST): weekly digest only."""
    if request.method != 'POST':
        return redirect('content:home')
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        _sub, created = NewsletterSubscriber.objects.update_or_create(
            email=email,
            defaults={'frequency': NewsletterSubscriber.FREQUENCY_WEEKLY},
        )
        if created:
            _send_newsletter_subscriber_welcome_email(email, request)
            messages.success(request, 'You are subscribed to the weekly digest.')
        else:
            messages.success(request, 'You are already subscribed to the weekly digest.')
    else:
        messages.warning(request, 'Please enter a valid email address.')
    referrer = request.META.get('HTTP_REFERER') or reverse('content:home')
    return redirect(referrer)


def newsletter_archive(request):
    """Public list of posted/sent newsletter issues (readers can save for later)."""
    issues = NewsletterIssue.objects.filter(
        status__in=[NewsletterIssue.STATUS_POSTED, NewsletterIssue.STATUS_SENT]
    ).prefetch_related('media_items').annotate(
        gallery_image_count=Count('media_items', filter=Q(media_items__image__isnull=False), distinct=True),
        like_count=Count('likes', distinct=True),
        bookmark_count=Count('bookmarked_by', distinct=True),
    ).order_by('-sent_at', '-posted_at', '-created_at')
    saved_ids = set()
    liked_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            BookmarkedNewsletterIssue.objects.filter(user=request.user)
            .values_list('newsletter_issue_id', flat=True)
        )
        liked_ids = set(
            NewsletterIssueLike.objects.filter(user=request.user).values_list('issue_id', flat=True)
        )
    return render(request, 'content/newsletter_archive.html', {
        'issues': issues,
        'saved_issue_ids': saved_ids,
        'liked_issue_ids': liked_ids,
    })


def newsletter_issue_detail(request, pk):
    """Single newsletter issue (posted/sent). Logged-in users can save."""
    issue = get_object_or_404(
        NewsletterIssue.objects.annotate(
            like_count=Count('likes', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
        ),
        pk=pk,
        status__in=[NewsletterIssue.STATUS_POSTED, NewsletterIssue.STATUS_SENT],
    )
    if _newsletter_issue_has_views_field():
        issue.views += 1
        issue.save(update_fields=['views'])
    is_bookmarked = False
    is_liked = False
    if request.user.is_authenticated:
        is_bookmarked = BookmarkedNewsletterIssue.objects.filter(
            user=request.user, newsletter_issue=issue
        ).exists()
        is_liked = NewsletterIssueLike.objects.filter(user=request.user, issue=issue).exists()
    public_like_count = display_like_public(
        issue.like_count, issue.pk, 'newsletter', publication_time_for_boost(issue, 'newsletter'),
    )
    public_save_count = display_save_public(
        issue.bookmark_count, issue.pk, 'newsletter', publication_time_for_boost(issue, 'newsletter'),
    )
    share_url = request.build_absolute_uri(issue.get_absolute_url())
    return render(request, 'content/newsletter_issue_detail.html', {
        'issue': issue,
        'is_bookmarked': is_bookmarked,
        'is_liked': is_liked,
        'public_like_count': public_like_count,
        'public_save_count': public_save_count,
        'share_url': share_url,
    })


@login_required
def newsletter_like_toggle(request, pk):
    """Toggle like on a newsletter issue; JSON for AJAX, redirect otherwise."""
    issue = get_object_or_404(
        NewsletterIssue,
        pk=pk,
        status__in=[NewsletterIssue.STATUS_POSTED, NewsletterIssue.STATUS_SENT],
    )
    like = NewsletterIssueLike.objects.filter(user=request.user, issue=issue).first()
    if like:
        like.delete()
    else:
        NewsletterIssueLike.objects.get_or_create(user=request.user, issue=issue)
    if _inline_toggle_ajax(request):
        like_count = display_like_public(
            issue.likes.count(), issue.pk, 'newsletter', publication_time_for_boost(issue, 'newsletter'),
        )
        liked = NewsletterIssueLike.objects.filter(user=request.user, issue=issue).exists()
        return JsonResponse({'ok': True, 'liked': liked, 'like_count': like_count})
    next_url = request.GET.get('next') or request.POST.get('next') or issue.get_absolute_url()
    return redirect(next_url)


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
            temp_post = form.instance
            ok, images, videos = _validate_extra_media_limits(form, temp_post, PostMedia, 'post')
            if not ok:
                return render(request, 'content/writer/post_form.html', {'form': form, 'post': None})
            post = form.save(commit=False)
            post.author = request.user
            post.status = 'draft'
            post.is_featured = False
            post.save()
            _save_extra_media_items(post, images, videos, PostMedia, 'post')
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
    post = get_object_or_404(Post.objects.prefetch_related('media_items'), pk=pk)
    if post.author != request.user:
        messages.error(request, 'You can only edit your own posts.')
        return redirect('content:writer_post_list')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            ok, images, videos = _validate_extra_media_limits(form, post, PostMedia, 'post')
            if not ok:
                return render(request, 'content/writer/post_form.html', {'form': form, 'post': post})
            # Keep status as draft for writers (they cannot publish)
            post = form.save(commit=False)
            post.author = request.user
            if post.status != 'published':
                post.status = 'draft'
            post.save()
            _save_extra_media_items(post, images, videos, PostMedia, 'post')
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
            temp_review = form.instance
            ok, images, videos = _validate_extra_media_limits(form, temp_review, ReviewMedia, 'review')
            if not ok:
                return render(request, 'content/writer/review_form.html', {'form': form, 'review': None})
            review = form.save(commit=False)
            review.author = request.user
            review.status = 'draft'
            review.save()
            _save_extra_media_items(review, images, videos, ReviewMedia, 'review')
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
    review = get_object_or_404(Review.objects.prefetch_related('media_items'), pk=pk)
    if review.author != request.user:
        messages.error(request, 'You can only edit your own reviews.')
        return redirect('content:writer_review_list')
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            ok, images, videos = _validate_extra_media_limits(form, review, ReviewMedia, 'review')
            if not ok:
                return render(request, 'content/writer/review_form.html', {'form': form, 'review': review})
            review = form.save(commit=False)
            review.author = request.user
            if review.status != 'published':
                review.status = 'draft'
            review.save()
            _save_extra_media_items(review, images, videos, ReviewMedia, 'review')
            messages.success(request, 'Review updated.')
            return redirect('content:writer_review_list')
    else:
        form = ReviewForm(instance=review)
    return render(request, 'content/writer/review_form.html', {'form': form, 'review': review})


# ----- CMS: Editor/Admin manage all posts, reviews, categories (in-site, no Django admin) -----

def _user_is_editor_or_admin(user):
    """User is superuser or in Editors group."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name='Editors').exists()


def _cms_redirect(request):
    """Redirect non-editor/admin away from CMS views."""
    from django.urls import reverse as rev
    if request.user.is_superuser:
        return redirect(rev('accounts:dashboard_admin'))
    if request.user.groups.filter(name='Writers').exists():
        return redirect(rev('accounts:dashboard_writer'))
    return redirect(rev('accounts:login'))


@login_required
def manage_post_list(request):
    """List all posts (editor/admin). Filter by status, featured, and mine (what I wrote or published)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    qs = Post.objects.select_related('category', 'author', 'published_by').order_by('-updated_at')
    status_filter = request.GET.get('status', '')
    featured_filter = request.GET.get('featured', '')
    mine_filter = request.GET.get('mine', '')
    if status_filter in ('draft', 'published'):
        qs = qs.filter(status=status_filter)
    if featured_filter == '1':
        qs = qs.filter(is_featured=True)
    if mine_filter == '1':
        qs = qs.filter(Q(author=request.user) | Q(published_by=request.user))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'content/cms/post_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'featured_filter': featured_filter,
        'mine_filter': mine_filter,
    })


@login_required
def manage_post_create(request):
    """Create a new post (editor/admin). Editors cannot self-publish; only another editor or admin can approve."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method == 'POST':
        form = PostFormEditor(request.POST, request.FILES)
        if form.is_valid():
            temp_post = form.instance
            ok, images, videos = _validate_extra_media_limits(form, temp_post, PostMedia, 'post')
            if not ok:
                editor_cannot_self_publish = not request.user.is_superuser
                if editor_cannot_self_publish:
                    form.fields['status'].choices = [('draft', 'Draft')]
                return render(request, 'content/cms/post_form.html', {
                    'form': form, 'post': None, 'editor_cannot_self_publish': editor_cannot_self_publish,
                })
            post = form.save(commit=False)
            post.author = request.user
            # Editors cannot publish their own content; must be approved by another editor or admin
            if not request.user.is_superuser and post.status == 'published':
                post.status = 'draft'
                post.published_at = None
                post.published_by = None
                messages.info(request, 'Saved as draft. Another editor or admin must approve and publish it.')
            elif post.status == 'published':
                if not post.published_at:
                    post.published_at = timezone.now()
                post.published_by = request.user
            post.save()
            _save_extra_media_items(post, images, videos, PostMedia, 'post')
            if request.user.is_superuser or post.status == 'published':
                messages.success(request, 'Post created.')
            return redirect('content:manage_post_list')
    else:
        form = PostFormEditor(initial={'status': 'draft'})
    editor_cannot_self_publish = not request.user.is_superuser
    if editor_cannot_self_publish:
        form.fields['status'].choices = [('draft', 'Draft')]
    return render(request, 'content/cms/post_form.html', {
        'form': form, 'post': None, 'editor_cannot_self_publish': editor_cannot_self_publish,
    })


@login_required
def manage_post_edit(request, pk):
    """Edit any post (editor/admin). Editors cannot publish their own; only another editor or admin can approve."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    post = get_object_or_404(
        Post.objects.select_related('category', 'author').prefetch_related('media_items'),
        pk=pk,
    )
    if request.method == 'POST':
        form = PostFormEditor(request.POST, request.FILES, instance=post)
        if form.is_valid():
            ok, images, videos = _validate_extra_media_limits(form, post, PostMedia, 'post')
            if not ok:
                editor_cannot_self_publish = not request.user.is_superuser and post.author_id == request.user.pk
                if editor_cannot_self_publish:
                    form.fields['status'].choices = [('draft', 'Draft')]
                return render(request, 'content/cms/post_form.html', {
                    'form': form, 'post': post, 'editor_cannot_self_publish': editor_cannot_self_publish,
                })
            post = form.save(commit=False)
            is_own = post.author_id == request.user.pk
            # Editors cannot publish their own content
            if not request.user.is_superuser and is_own and post.status == 'published':
                post.status = 'draft'
                post.published_at = None
                post.published_by = None
                messages.info(request, 'Your own posts must be approved by another editor or admin. Saved as draft.')
            elif post.status == 'published':
                if not post.published_at:
                    post.published_at = timezone.now()
                post.published_by = request.user
            post.save()
            _save_extra_media_items(post, images, videos, PostMedia, 'post')
            if not (not request.user.is_superuser and is_own and form.cleaned_data.get('status') == 'published'):
                messages.success(request, 'Post updated.')
            return redirect('content:manage_post_list')
    else:
        form = PostFormEditor(instance=post)
    editor_cannot_self_publish = not request.user.is_superuser and post.author_id == request.user.pk
    if editor_cannot_self_publish:
        form.fields['status'].choices = [('draft', 'Draft')]
    return render(request, 'content/cms/post_form.html', {
        'form': form, 'post': post, 'editor_cannot_self_publish': editor_cannot_self_publish,
    })


@login_required
def manage_post_delete(request, pk):
    """Delete a post. Admin can always delete. Editor can delete drafts or content they themselves published."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    post = get_object_or_404(Post, pk=pk)
    if post.status == 'published' and not request.user.is_superuser:
        if post.published_by_id != request.user.pk:
            messages.error(request, 'Only the admin or the person who published this can delete it. Ask an admin to delete.')
            return redirect('content:manage_post_list')
    if request.method == 'POST':
        title = post.title
        post.delete()
        messages.success(request, f'Post "{title}" deleted.')
        return redirect('content:manage_post_list')
    return render(request, 'content/cms/post_confirm_delete.html', {'post': post})


@login_required
def manage_review_list(request):
    """List all reviews (editor/admin). Filter by status and mine (what I wrote or published)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    qs = Review.objects.select_related('author', 'published_by').order_by('-updated_at')
    status_filter = request.GET.get('status', '')
    mine_filter = request.GET.get('mine', '')
    if status_filter in ('draft', 'published'):
        qs = qs.filter(status=status_filter)
    if mine_filter == '1':
        qs = qs.filter(Q(author=request.user) | Q(published_by=request.user))
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'content/cms/review_list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'mine_filter': mine_filter,
    })


@login_required
def manage_review_create(request):
    """Create a new review (editor/admin). Editors cannot self-publish; only another editor or admin can approve."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method == 'POST':
        form = ReviewFormEditor(request.POST, request.FILES)
        if form.is_valid():
            temp_review = form.instance
            ok, images, videos = _validate_extra_media_limits(form, temp_review, ReviewMedia, 'review')
            if not ok:
                editor_cannot_self_publish = not request.user.is_superuser
                if editor_cannot_self_publish:
                    form.fields['status'].choices = [('draft', 'Draft')]
                return render(request, 'content/cms/review_form.html', {
                    'form': form, 'review': None, 'editor_cannot_self_publish': editor_cannot_self_publish,
                })
            review = form.save(commit=False)
            review.author = request.user
            if not request.user.is_superuser and review.status == 'published':
                review.status = 'draft'
                review.published_at = None
                review.published_by = None
                messages.info(request, 'Saved as draft. Another editor or admin must approve and publish it.')
            elif review.status == 'published':
                if not review.published_at:
                    review.published_at = timezone.now()
                review.published_by = request.user
            review.save()
            _save_extra_media_items(review, images, videos, ReviewMedia, 'review')
            if request.user.is_superuser or review.status == 'published':
                messages.success(request, 'Review created.')
            return redirect('content:manage_review_list')
    else:
        form = ReviewFormEditor(initial={'status': 'draft'})
    editor_cannot_self_publish = not request.user.is_superuser
    if editor_cannot_self_publish:
        form.fields['status'].choices = [('draft', 'Draft')]
    return render(request, 'content/cms/review_form.html', {
        'form': form, 'review': None, 'editor_cannot_self_publish': editor_cannot_self_publish,
    })


@login_required
def manage_review_edit(request, pk):
    """Edit any review (editor/admin). Editors cannot publish their own; only another editor or admin can approve."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    review = get_object_or_404(Review.objects.prefetch_related('media_items'), pk=pk)
    if request.method == 'POST':
        form = ReviewFormEditor(request.POST, request.FILES, instance=review)
        if form.is_valid():
            ok, images, videos = _validate_extra_media_limits(form, review, ReviewMedia, 'review')
            if not ok:
                editor_cannot_self_publish = not request.user.is_superuser and review.author_id == request.user.pk
                if editor_cannot_self_publish:
                    form.fields['status'].choices = [('draft', 'Draft')]
                return render(request, 'content/cms/review_form.html', {
                    'form': form, 'review': review, 'editor_cannot_self_publish': editor_cannot_self_publish,
                })
            review = form.save(commit=False)
            is_own = review.author_id == request.user.pk
            if not request.user.is_superuser and is_own and review.status == 'published':
                review.status = 'draft'
                review.published_at = None
                review.published_by = None
                messages.info(request, 'Your own reviews must be approved by another editor or admin. Saved as draft.')
            elif review.status == 'published':
                if not review.published_at:
                    review.published_at = timezone.now()
                review.published_by = request.user
            review.save()
            _save_extra_media_items(review, images, videos, ReviewMedia, 'review')
            if not (not request.user.is_superuser and is_own and form.cleaned_data.get('status') == 'published'):
                messages.success(request, 'Review updated.')
            return redirect('content:manage_review_list')
    else:
        form = ReviewFormEditor(instance=review)
    editor_cannot_self_publish = not request.user.is_superuser and review.author_id == request.user.pk
    if editor_cannot_self_publish:
        form.fields['status'].choices = [('draft', 'Draft')]
    return render(request, 'content/cms/review_form.html', {
        'form': form, 'review': review, 'editor_cannot_self_publish': editor_cannot_self_publish,
    })


@login_required
def manage_review_delete(request, pk):
    """Delete a review. Admin can always delete. Editor can delete drafts or content they themselves published."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    review = get_object_or_404(Review, pk=pk)
    if review.status == 'published' and not request.user.is_superuser:
        if review.published_by_id != request.user.pk:
            messages.error(request, 'Only the admin or the person who published this can delete it. Ask an admin to delete.')
            return redirect('content:manage_review_list')
    if request.method == 'POST':
        title = review.title
        review.delete()
        messages.success(request, f'Review "{title}" deleted.')
        return redirect('content:manage_review_list')
    return render(request, 'content/cms/review_confirm_delete.html', {'review': review})


@login_required
def manage_category_list(request):
    """List all categories (editor/admin)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    categories = Category.objects.annotate(
        post_count=Count('posts'),
    ).order_by('name')
    return render(request, 'content/cms/category_list.html', {'categories': categories})


@login_required
def manage_category_create(request):
    """Create a category (editor/admin)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created.')
            return redirect('content:manage_category_list')
    else:
        form = CategoryForm()
    return render(request, 'content/cms/category_form.html', {'form': form, 'category': None})


@login_required
def manage_category_edit(request, pk):
    """Edit a category (editor/admin)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated.')
            return redirect('content:manage_category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'content/cms/category_form.html', {'form': form, 'category': category})


@login_required
def manage_category_delete(request, pk):
    """Delete a category (editor/admin)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f'Category "{name}" deleted.')
        return redirect('content:manage_category_list')
    return render(request, 'content/cms/category_confirm_delete.html', {'category': category})


# ----- Newsletter issues: create, list, edit, send (editor/admin) -----

@login_required
def manage_newsletter_list(request):
    """Main newsletter CMS page: active items + quick summary."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    issues = NewsletterIssue.objects.order_by('-created_at')
    schedule = _weekly_digest_schedule_context()
    week_start = timezone.now() - timedelta(days=7)
    posted_current = issues.filter(status=NewsletterIssue.STATUS_POSTED, posted_at__gte=week_start)
    posted_older = issues.filter(status=NewsletterIssue.STATUS_POSTED).exclude(pk__in=posted_current.values('pk'))
    sent_recent = issues.filter(status=NewsletterIssue.STATUS_SENT)[:5]
    return render(request, 'content/cms/newsletter_list.html', {
        'issues': issues,
        'draft_issues': issues.filter(status=NewsletterIssue.STATUS_DRAFT),
        'posted_issues': posted_current,
        'posted_older_issues': posted_older,
        'posted_older_count': posted_older.count(),
        'sent_recent_issues': sent_recent,
        'sent_total_count': issues.filter(status=NewsletterIssue.STATUS_SENT).count(),
        'weekly_digest_schedule_text': schedule['human_text'],
        'weekly_digest_max_items': schedule['max_items'],
    })


@login_required
def manage_newsletter_sent_archive(request):
    """Paginated archive page for sent newsletters."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    sent_qs = NewsletterIssue.objects.filter(status=NewsletterIssue.STATUS_SENT).order_by('-sent_at', '-created_at')
    paginator = Paginator(sent_qs, 24)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'content/cms/newsletter_sent_archive.html', {
        'page_obj': page_obj,
        'sent_total_count': sent_qs.count(),
    })


@login_required
def manage_newsletter_create(request):
    """Create a new newsletter issue (draft)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method == 'POST':
        form = NewsletterIssueForm(request.POST, request.FILES)
        if form.is_valid():
            temp_issue = form.instance
            ok, images, videos = _validate_extra_media_limits(form, temp_issue, NewsletterIssueMedia, 'issue')
            if not ok:
                return render(request, 'content/cms/newsletter_form.html', {'form': form, 'issue': None})
            issue = form.save(commit=False)
            issue.created_by = request.user
            issue.save()
            _save_extra_media_items(issue, images, videos, NewsletterIssueMedia, 'issue')
            messages.success(request, 'Newsletter draft created. You can edit and send it from the list.')
            return redirect('content:manage_newsletter_list')
    else:
        form = NewsletterIssueForm()
    return render(request, 'content/cms/newsletter_form.html', {'form': form, 'issue': None})


@login_required
def manage_newsletter_edit(request, pk):
    """Edit a newsletter issue (only drafts)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    issue = get_object_or_404(NewsletterIssue.objects.prefetch_related('media_items'), pk=pk)
    if issue.status == NewsletterIssue.STATUS_SENT:
        messages.warning(request, 'This newsletter was already sent. Create a new one for another send.')
        return redirect('content:manage_newsletter_list')
    if request.method == 'POST':
        form = NewsletterIssueForm(request.POST, request.FILES, instance=issue)
        if form.is_valid():
            ok, images, videos = _validate_extra_media_limits(form, issue, NewsletterIssueMedia, 'issue')
            if not ok:
                return render(request, 'content/cms/newsletter_form.html', {'form': form, 'issue': issue})
            form.save()
            _save_extra_media_items(issue, images, videos, NewsletterIssueMedia, 'issue')
            messages.success(request, 'Newsletter draft updated.')
            return redirect('content:manage_newsletter_list')
    else:
        form = NewsletterIssueForm(instance=issue)
    return render(request, 'content/cms/newsletter_form.html', {'form': form, 'issue': issue})


@login_required
def manage_newsletter_delete(request, pk):
    """Delete a newsletter issue (editor/admin)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    if request.method != 'POST':
        messages.warning(request, 'Use the delete button to remove a newsletter.')
        return redirect('content:manage_newsletter_list')
    title = issue.title
    issue.delete()
    messages.success(request, f'Newsletter "{title}" deleted.')
    return redirect('content:manage_newsletter_list')


@login_required
def manage_newsletter_post(request, pk):
    """Post a newsletter on-site without emailing subscribers."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    if issue.status == NewsletterIssue.STATUS_SENT:
        messages.warning(request, 'This newsletter was already sent and is already public.')
        return redirect('content:manage_newsletter_list')
    issue.status = NewsletterIssue.STATUS_POSTED
    if not issue.posted_at:
        issue.posted_at = timezone.now()
    issue.save(update_fields=['status', 'posted_at'])
    messages.success(request, 'Newsletter posted on the site (not emailed).')
    return redirect('content:manage_newsletter_list')


@login_required
def manage_newsletter_send(request, pk):
    """Send a newsletter issue to all subscribers. One-time; marks issue as sent."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    if issue.status == NewsletterIssue.STATUS_SENT:
        messages.warning(request, 'This newsletter was already sent. Use Resend to mail it again.')
        return redirect('content:manage_newsletter_list')
    sent, send_err = _send_newsletter_issue_to_subscribers(issue)
    if sent == 0:
        if send_err:
            messages.error(request, send_err)
        else:
            messages.warning(request, 'No subscribers. Add emails via newsletter signup on the site.')
        return redirect('content:manage_newsletter_list')
    messages.success(request, f'Newsletter sent to {sent} subscriber(s).')
    return redirect('content:manage_newsletter_list')


@login_required
def manage_newsletter_resend(request, pk):
    """Send a copy of an already-sent issue to all subscribers again (does not change status)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method != 'POST':
        messages.warning(request, 'Confirm resend using the Resend button.')
        return redirect('content:manage_newsletter_list')
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    if issue.status != NewsletterIssue.STATUS_SENT:
        messages.warning(request, 'Only newsletters in Sent status can be resent.')
        return redirect('content:manage_newsletter_list')
    if not NewsletterSubscriber.objects.exists():
        messages.warning(request, 'No subscribers. Add emails via newsletter signup on the site.')
        return redirect('content:manage_newsletter_list')
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    subject = f'{site_name} — {issue.title}'
    sent, failed, first_err = _broadcast_newsletter_emails(subject, issue.content or '', is_html=False)
    total = sent + failed
    if sent > 0 and failed == 0:
        messages.success(request, f'Resent to {sent} subscriber(s).')
    elif sent > 0 and failed > 0:
        messages.warning(
            request,
            f'Partial delivery: reached {sent} of {total} subscriber(s). {failed} failed.'
            f'{f" First error: {first_err}" if first_err else ""}',
        )
    elif sent == 0 and failed > 0:
        messages.error(
            request,
            f'Resend did not reach any inbox.{f" ({first_err})" if first_err else ""}',
        )
    elif sent == 0 and failed == 0:
        if first_err:
            messages.error(request, first_err)
        else:
            messages.warning(request, 'No emails were delivered.')
    referrer = request.META.get('HTTP_REFERER')
    if referrer and url_has_allowed_host_and_scheme(
        referrer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referrer)
    return redirect('content:manage_newsletter_list')


@login_required
def manage_newsletter_unsend_to_posted(request, pk):
    """Move a sent issue back to Posted (not marked emailed) so it can join batch send again."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method != 'POST':
        messages.warning(request, 'Use the Back to Posted button.')
        return redirect('content:manage_newsletter_list')
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    if issue.status != NewsletterIssue.STATUS_SENT:
        messages.warning(request, 'Only sent newsletters can be moved back to Posted.')
        return redirect('content:manage_newsletter_list')
    title = issue.title
    issue.status = NewsletterIssue.STATUS_POSTED
    issue.sent_at = None
    if not issue.posted_at:
        issue.posted_at = timezone.now()
    issue.save(update_fields=['status', 'sent_at', 'posted_at'])
    messages.success(request, f'"{title}" is back in Posted (ready for Send / Send top).')
    referrer = request.META.get('HTTP_REFERER')
    if referrer and url_has_allowed_host_and_scheme(
        referrer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referrer)
    return redirect('content:manage_newsletter_list')


@login_required
def manage_newsletter_unsend_all_sent_to_posted(request):
    """Move every sent issue back to Posted for re-testing batch sends."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    if request.method != 'POST':
        messages.warning(request, 'Use the form to move all sent newsletters back to Posted.')
        return redirect('content:manage_newsletter_list')
    qs = NewsletterIssue.objects.filter(status=NewsletterIssue.STATUS_SENT).order_by('pk')
    count = qs.count()
    if count == 0:
        messages.info(request, 'No sent newsletters to move.')
        return redirect('content:manage_newsletter_list')
    now = timezone.now()
    for issue in qs:
        issue.status = NewsletterIssue.STATUS_POSTED
        issue.sent_at = None
        if not issue.posted_at:
            issue.posted_at = now
        issue.save(update_fields=['status', 'sent_at', 'posted_at'])
    messages.success(
        request,
        f'Moved {count} newsletter(s) from Sent to Posted. Use “Send top” or per-issue Send when ready.',
    )
    return redirect('content:manage_newsletter_list')


def _site_public_base_url():
    """Base URL for issue links in emails when there is no HttpRequest (e.g. cron)."""
    explicit = getattr(settings, 'SITE_PUBLIC_BASE_URL', '').strip().rstrip('/')
    if explicit:
        return explicit
    for host in settings.ALLOWED_HOSTS:
        h = (host or '').strip()
        if h and h not in ('localhost', '127.0.0.1', 'testserver', '[::1]'):
            return f'https://{h}'
    return 'http://127.0.0.1:8000'


def _digest_items_from_newsletter_issues(issues, build_absolute_uri):
    """Build digest item dicts (title, url, excerpt) for template content/emails/digest.html."""
    items = []
    for obj in issues:
        raw = (obj.content or '').replace('\n', ' ').strip()
        excerpt = raw[:200] + ('...' if len(raw) > 200 else '')
        items.append({
            'title': obj.title,
            'url': build_absolute_uri(obj),
            'excerpt': excerpt,
            'type_label': 'Newsletter',
        })
    return items


def _newsletter_digest_social_links():
    """Linked list of {label, url} for digest footer; empty entries omitted."""
    links = []
    for label, attr in (
        ('LinkedIn', 'SOCIAL_LINKEDIN_URL'),
        ('Instagram', 'SOCIAL_INSTAGRAM_URL'),
        ('Facebook', 'SOCIAL_FACEBOOK_URL'),
    ):
        url = (getattr(settings, attr, '') or '').strip()
        if url:
            links.append({'label': label, 'url': url})
    return links


def _render_newsletter_digest_email(
    site_name,
    date_label,
    items,
    *,
    digest_intro,
    subscription_note,
    unsubscribe_hint,
):
    return render_to_string('content/emails/digest.html', {
        'site_name': site_name,
        'date_label': date_label,
        'digest_intro': digest_intro,
        'subscription_note': subscription_note,
        'items': items,
        'unsubscribe_hint': unsubscribe_hint,
        'social_links': _newsletter_digest_social_links(),
    })


def _send_newsletter_subscriber_welcome_email(to_email, request=None):
    """Send a one-time welcome when a new NewsletterSubscriber row is created."""
    to_email = (to_email or '').strip()
    if not to_email or not getattr(settings, 'NEWSLETTER_SEND_WELCOME_EMAIL', True):
        return
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    if request:
        home_url = request.build_absolute_uri(reverse('content:home'))
        archive_url = request.build_absolute_uri(reverse('content:newsletter_archive'))
        unsubscribe_hint = request.build_absolute_uri(reverse('content:home')) + '#newsletter'
    else:
        base = _site_public_base_url().rstrip('/')
        home_url = f'{base}{reverse("content:home")}'
        archive_url = f'{base}{reverse("content:newsletter_archive")}'
        unsubscribe_hint = f'{base}{reverse("content:home")}#newsletter'
    ctx = {
        'site_name': site_name,
        'home_url': home_url,
        'archive_url': archive_url,
        'unsubscribe_hint': unsubscribe_hint,
        'social_links': _newsletter_digest_social_links(),
    }
    html = render_to_string('content/emails/newsletter_welcome.html', ctx)
    text_body = render_to_string('content/emails/newsletter_welcome.txt', ctx)
    subject = f'You are subscribed — {site_name}'
    _send_transactional_newsletter_style_email(
        to_email,
        subject,
        text_body=text_body,
        html_body=html,
    )


@login_required
def manage_newsletter_send_posted(request):
    """Send one email to all subscribers: top posted issues as linked topics (viral-ranked cap)."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    max_items = int(getattr(settings, 'WEEKLY_DIGEST_MAX_ITEMS', 12))
    max_items = max(1, max_items)
    posted_issues = list(
        NewsletterIssue.objects.filter(status=NewsletterIssue.STATUS_POSTED)
        .annotate(
            like_count=Count('likes', distinct=True),
            bookmark_count=Count('bookmarked_by', distinct=True),
        )
        .order_by('-like_count', '-bookmark_count', '-posted_at', '-created_at')[:max_items]
    )
    if not posted_issues:
        messages.warning(request, 'No posted newsletters to send.')
        return redirect('content:manage_newsletter_list')
    if not NewsletterSubscriber.objects.exists():
        messages.warning(request, 'No subscribers. Add emails via newsletter signup on the site.')
        return redirect('content:manage_newsletter_list')
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    date_label = timezone.now().strftime('%d %b %Y')
    n = len(posted_issues)
    digest_intro = (
        f'Here are {n} newsletter topic{"s" if n != 1 else ""} in one message. '
        'Click a title to read the full issue on our site.'
    )
    items = _digest_items_from_newsletter_issues(
        posted_issues,
        lambda o: request.build_absolute_uri(o.get_absolute_url()),
    )
    html = _render_newsletter_digest_email(
        site_name,
        date_label,
        items,
        digest_intro=digest_intro,
        subscription_note='newsletter topics',
        unsubscribe_hint=request.build_absolute_uri(reverse('content:home')) + '#newsletter',
    )
    subject = f'{site_name} — {n} newsletter topic{"s" if n != 1 else ""} ({date_label})'
    sent, failed, first_err = _broadcast_newsletter_emails(subject, html, is_html=True)
    if sent > 0:
        now = timezone.now()
        for issue in posted_issues:
            issue.status = NewsletterIssue.STATUS_SENT
            issue.sent_at = now
            if not issue.posted_at:
                issue.posted_at = now
            issue.save(update_fields=['status', 'sent_at', 'posted_at'])
        msg = (
            f'One roundup email sent to {sent} subscriber(s) with {n} topic link{"s" if n != 1 else ""}.'
        )
        if failed:
            messages.warning(
                request,
                f'{msg} {failed} delivery failure(s).{f" First error: {first_err}" if first_err else ""}',
            )
        else:
            messages.success(request, msg)
    else:
        if first_err:
            messages.error(request, first_err)
        else:
            messages.warning(request, 'No emails were delivered. Check subscribers and SMTP settings.')
    return redirect('content:manage_newsletter_list')


def _send_transactional_newsletter_style_email(to_email, subject, *, text_body, html_body=None):
    """Send one message to one address using newsletter SMTP when configured (welcome, etc.)."""
    to_email = (to_email or '').strip()
    if not to_email:
        return False
    from_email = getattr(settings, 'NEWSLETTER_FROM_EMAIL', 'newsletter@next251.com')
    use_newsletter_smtp = (
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_USER', '') and
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_PASSWORD', '')
    )
    is_html = html_body is not None
    body = html_body if is_html else text_body
    conn = None
    try:
        if use_newsletter_smtp:
            conn = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=settings.EMAIL_HOST,
                port=int(getattr(settings, 'EMAIL_PORT', 587)),
                username=settings.NEWSLETTER_EMAIL_HOST_USER,
                password=settings.NEWSLETTER_EMAIL_HOST_PASSWORD,
                use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
                fail_silently=False,
            )
        if conn:
            msg = EmailMessage(subject, body, from_email, [to_email], connection=conn)
            if is_html:
                msg.content_subtype = 'html'
            msg.send(fail_silently=False)
        elif is_html:
            send_mail(
                subject,
                text_body or 'Thanks for subscribing.',
                from_email,
                [to_email],
                fail_silently=False,
                html_message=html_body,
            )
        else:
            send_mail(subject, text_body, from_email, [to_email], fail_silently=False, html_message=None)
        return True
    except Exception as exc:
        logger.warning(
            'Transactional newsletter email to %s failed: %s',
            to_email,
            exc,
            exc_info=True,
        )
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _broadcast_newsletter_emails(subject, body, *, is_html=False):
    """Send one message per subscriber. Returns (delivered_count, failed_count, first_error_message)."""
    subscribers = list(NewsletterSubscriber.objects.values_list('email', flat=True))
    if not subscribers:
        return 0, 0, None
    from_email = getattr(settings, 'NEWSLETTER_FROM_EMAIL', 'newsletter@next251.com')
    use_newsletter_smtp = (
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_USER', '') and
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_PASSWORD', '')
    )
    if not use_newsletter_smtp:
        backend = getattr(settings, 'EMAIL_BACKEND', '') or ''
        if 'console' in backend:
            return 0, 0, (
                'Real email is not enabled: Django is using the console backend, so nothing is sent to real inboxes. '
                'In .env set USE_REAL_EMAIL=1 and SMTP (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD), '
                'or set NEWSLETTER_EMAIL_HOST_USER and NEWSLETTER_EMAIL_HOST_PASSWORD to send newsletters via SMTP '
                'while keeping the default backend on console for other mail.'
            )
    sent = 0
    failed = 0
    first_error = None
    for to_email in subscribers:
        conn = None
        try:
            if use_newsletter_smtp:
                conn = get_connection(
                    backend='django.core.mail.backends.smtp.EmailBackend',
                    host=settings.EMAIL_HOST,
                    port=int(getattr(settings, 'EMAIL_PORT', 587)),
                    username=settings.NEWSLETTER_EMAIL_HOST_USER,
                    password=settings.NEWSLETTER_EMAIL_HOST_PASSWORD,
                    use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
                    use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
                    fail_silently=False,
                )
                msg = EmailMessage(subject, body, from_email, [to_email], connection=conn)
                if is_html:
                    msg.content_subtype = 'html'
                result = msg.send(fail_silently=False)
            elif is_html:
                result = send_mail(
                    subject, 'View this message on our site.', from_email, [to_email],
                    fail_silently=False, html_message=body,
                )
            else:
                result = send_mail(subject, body, from_email, [to_email], fail_silently=False, html_message=None)
            sent += int(result or 0)
        except Exception as exc:
            failed += 1
            logger.warning('Newsletter email failed for %s: %s', to_email, exc, exc_info=True)
            if first_error is None:
                first_error = str(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    return sent, failed, first_error


def _send_newsletter_issue_to_subscribers(issue):
    """Send one issue to all subscribers and mark it sent. Returns (delivered_count, error_message_or_none)."""
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    subject = f'{site_name} — {issue.title}'
    sent, _failed, first_err = _broadcast_newsletter_emails(subject, issue.content or '', is_html=False)
    if sent == 0:
        return 0, first_err
    issue.status = NewsletterIssue.STATUS_SENT
    if not issue.posted_at:
        issue.posted_at = timezone.now()
    issue.sent_at = timezone.now()
    issue.save(update_fields=['status', 'posted_at', 'sent_at'])
    return sent, None


def _weekly_digest_schedule_context():
    """Resolved weekly digest schedule settings with safe defaults."""
    tz_name = getattr(settings, 'WEEKLY_DIGEST_TIMEZONE', 'Africa/Addis_Ababa')
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz_name = 'UTC'
        tz = ZoneInfo('UTC')
    weekday = int(getattr(settings, 'WEEKLY_DIGEST_SEND_WEEKDAY', 4))
    weekday = max(0, min(6, weekday))
    hour = int(getattr(settings, 'WEEKLY_DIGEST_SEND_HOUR', 20))
    minute = int(getattr(settings, 'WEEKLY_DIGEST_SEND_MINUTE', 0))
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    window_minutes = int(getattr(settings, 'WEEKLY_DIGEST_SEND_WINDOW_MINUTES', 120))
    window_minutes = max(1, window_minutes)
    max_items = int(getattr(settings, 'WEEKLY_DIGEST_MAX_ITEMS', 12))
    max_items = max(1, max_items)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    human_text = f"{day_names[weekday]} at {hour:02d}:{minute:02d} ({tz_name}), ±{window_minutes} minutes"
    return {
        'tz': tz,
        'tz_name': tz_name,
        'weekday': weekday,
        'hour': hour,
        'minute': minute,
        'window_minutes': window_minutes,
        'max_items': max_items,
        'human_text': human_text,
    }


def _weekly_digest_is_within_window(now_utc, schedule):
    """Allow send only around configured weekly slot."""
    local_now = timezone.localtime(now_utc, schedule['tz'])
    if local_now.weekday() != schedule['weekday']:
        return False, local_now
    current_minutes = local_now.hour * 60 + local_now.minute
    target_minutes = schedule['hour'] * 60 + schedule['minute']
    return abs(current_minutes - target_minutes) <= schedule['window_minutes'], local_now


def _weekly_newsletter_digest_items_and_html(request, since, date_label, max_items):
    """Build weekly digest from posted/sent newsletter topics only (configurable cap)."""
    issues = (
        NewsletterIssue.objects.filter(
            status__in=[NewsletterIssue.STATUS_POSTED, NewsletterIssue.STATUS_SENT],
        )
        .filter(Q(posted_at__gte=since) | Q(sent_at__gte=since) | Q(created_at__gte=since))
        .annotate(bookmark_count=Count('bookmarked_by'))
        .order_by('-bookmark_count', '-sent_at', '-posted_at', '-created_at')[:max_items]
    )
    items = _digest_items_from_newsletter_issues(
        issues,
        lambda o: request.build_absolute_uri(o.get_absolute_url()),
    )
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    digest_intro = (
        'Weekly newsletter topics (up to 12). Click a topic title to read the full newsletter on our site.'
    )
    html = _render_newsletter_digest_email(
        site_name,
        date_label,
        items,
        digest_intro=digest_intro,
        subscription_note='weekly digest',
        unsubscribe_hint=request.build_absolute_uri(reverse('content:home')) + '#newsletter',
    )
    return items, html


@login_required
def send_daily_digest(request):
    """Send one bundled daily digest (last 24h of articles + reviews) to subscribers who chose daily."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    messages.info(request, 'Daily digest is disabled. This site now uses weekly digest only.')
    return redirect('content:manage_newsletter_list')


@login_required
def send_weekly_digest(request):
    """Send one bundled weekly digest (last 7 days) to subscribers who chose weekly."""
    if not _user_is_editor_or_admin(request.user):
        return _cms_redirect(request)
    now_utc = timezone.now()
    schedule = _weekly_digest_schedule_context()
    in_window, local_now = _weekly_digest_is_within_window(now_utc, schedule)
    if not in_window:
        messages.warning(
            request,
            f'Weekly digest can be sent only on {schedule["human_text"]}. '
            f'Current local time: {local_now.strftime("%A %H:%M")} ({schedule["tz_name"]}).'
        )
        return redirect('content:manage_newsletter_list')
    since = now_utc - timedelta(days=7)
    date_label = f"Week of {since.strftime('%d %b')} – {now_utc.strftime('%d %b %Y')}"
    items, html = _weekly_newsletter_digest_items_and_html(request, since, date_label, schedule['max_items'])
    if not items:
        messages.warning(request, 'No posted/sent newsletters found for this week.')
        return redirect('content:manage_newsletter_list')
    subscribers = list(NewsletterSubscriber.objects.filter(frequency=NewsletterSubscriber.FREQUENCY_WEEKLY).values_list('email', flat=True))
    if not subscribers:
        messages.warning(request, 'No subscribers with “Weekly” preference.')
        return redirect('content:manage_newsletter_list')
    from_email = getattr(settings, 'NEWSLETTER_FROM_EMAIL', 'newsletter@next251.com')
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    subject = f'{site_name} — Weekly newsletter topics ({timezone.now().strftime("%d %b %Y")})'
    issue = NewsletterIssue.objects.create(
        title=f'Weekly digest — {date_label}',
        content=html,
        status=NewsletterIssue.STATUS_SENT,
        posted_at=timezone.now(),
        sent_at=timezone.now(),
        created_by=request.user,
    )
    use_newsletter_smtp = (
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_USER', '') and
        getattr(settings, 'NEWSLETTER_EMAIL_HOST_PASSWORD', '')
    )
    if use_newsletter_smtp:
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=getattr(settings, 'EMAIL_HOST', ''),
            port=getattr(settings, 'EMAIL_PORT', 587),
            username=settings.NEWSLETTER_EMAIL_HOST_USER,
            password=settings.NEWSLETTER_EMAIL_HOST_PASSWORD,
            use_tls=getattr(settings, 'EMAIL_USE_TLS', True),
            use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
            fail_silently=False,
        )
    else:
        connection = None
    sent = 0
    failed = 0
    for to_email in subscribers:
        try:
            if connection:
                msg = EmailMessage(subject, html, from_email, [to_email], connection=connection)
                msg.content_subtype = 'html'
                result = msg.send(fail_silently=False)
            else:
                result = send_mail(subject, 'View the digest on our site.', from_email, [to_email], fail_silently=False, html_message=html)
            sent += int(result or 0)
        except Exception:
            failed += 1
            continue
    if sent > 0:
        messages.success(request, f'Weekly digest sent to {sent} subscriber(s). One email with the week’s news.')
        if failed:
            messages.warning(request, f'{failed} email(s) failed to deliver. Check SMTP credentials and server logs.')
    else:
        messages.warning(request, 'No digest emails were delivered. Check SMTP credentials and email server settings.')
    return redirect('content:manage_newsletter_list')
