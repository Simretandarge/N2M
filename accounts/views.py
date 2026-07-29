"""
Account views: signup, login, logout, password reset, profile, role-based dashboard.
"""
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import Group
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone

from django.contrib.auth import get_user_model
from .forms import SignUpForm, ProfileForm, WriterApplicationForm, EditorApplicationForm, UserEditForm
from .models import (
    WriterApplication,
    EditorApplication,
    BookmarkedPost,
    BookmarkedReview,
    BookmarkedNewsletterIssue,
    ReaderPreference,
    UserProfile,
)

User = get_user_model()


def _inline_toggle_ajax(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
        or request.GET.get('ajax') == '1'
    )


def _add_user_to_newsletter(user, request=None):
    """Add user's email to newsletter list on signup (for weekly insights)."""
    if not user.email:
        return
    try:
        from content.models import NewsletterSubscriber
        from content.views import _send_newsletter_subscriber_welcome_email

        _sub, created = NewsletterSubscriber.objects.get_or_create(
            email=user.email,
            defaults={'frequency': NewsletterSubscriber.FREQUENCY_WEEKLY},
        )
        if created:
            _send_newsletter_subscriber_welcome_email(user.email, request)
    except Exception:
        pass


def _send_welcome_email(user, request):
    """Send welcome email after signup. Uses console backend in dev."""
    if not user.email:
        return
    site_name = getattr(settings, 'SITE_NAME', 'Next 251 Media')
    tagline = getattr(settings, 'SITE_TAGLINE', "Shaping What's Next.")
    account_url = request.build_absolute_uri(reverse('reader:account_settings'))
    home_url = request.build_absolute_uri(reverse('content:home'))
    ctx = {
        'user': user,
        'site_name': site_name,
        'tagline': tagline,
        'account_url': account_url,
        'home_url': home_url,
    }
    subject = render_to_string('accounts/welcome_email_subject.txt', ctx).strip().replace('\n', ' ')
    body = render_to_string('accounts/welcome_email.txt', ctx)
    send_mail(
        subject,
        body,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@next251.com'),
        [user.email],
        fail_silently=True,
    )


def _user_role(user):
    """Return 'admin', 'editor', 'writer', or 'reader'."""
    if user.is_superuser:
        return 'admin'
    if user.groups.filter(name='Editors').exists():
        return 'editor'
    if user.groups.filter(name='Writers').exists():
        return 'writer'
    return 'reader'


def signup(request):
    """User registration. Redirects to ?next= if present (e.g. back to article)."""
    if request.user.is_authenticated:
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            ReaderPreference.objects.get_or_create(user=user)
            _add_user_to_newsletter(user, request)
            _send_welcome_email(user, request)
            login(request, user)
            messages.success(request, 'Account created. Welcome! Check your email for a quick guide.')
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form, 'next': request.GET.get('next')})


class SignInView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        role = _user_role(self.request.user)
        if role == 'admin':
            return resolve_url('accounts:dashboard_admin')
        if role == 'editor':
            return resolve_url('accounts:dashboard_editor')
        if role == 'writer':
            return resolve_url('accounts:dashboard_writer')
        return resolve_url('content:home')


class SignOutView(LogoutView):
    next_page = 'content:home'


class ForgotPasswordView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    subject_template_name = 'accounts/password_reset_subject.txt'
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@next251.com')


class ForgotPasswordDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class ForgotPasswordConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class ForgotPasswordCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


def _redirect_to_role_dashboard(user):
    """Redirect URL for the user's role (admin / editor / writer / reader)."""
    role = _user_role(user)
    if role == 'admin':
        return redirect('accounts:dashboard_admin')
    if role == 'editor':
        return redirect('accounts:dashboard_editor')
    if role == 'writer':
        return redirect('accounts:dashboard_writer')
    return redirect('reader:account_settings')


@login_required
def dashboard(request):
    """Single dashboard entry: redirect to the correct role-specific dashboard."""
    return _redirect_to_role_dashboard(request.user)


@login_required
def dashboard_admin(request):
    """Admin-only dashboard. Editors and writers are redirected to their own."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post, Review
    editor_pending = EditorApplication.objects.filter(status=EditorApplication.STATUS_PENDING).count()
    writer_pending = WriterApplication.objects.filter(status=WriterApplication.STATUS_PENDING).count()
    context = {
        'role': 'admin',
        'total_posts': Post.objects.count(),
        'published_posts': Post.objects.filter(status='published').count(),
        'total_reviews': Review.objects.count(),
        'draft_posts': Post.objects.filter(status='draft').count(),
        'editor_applications_pending': editor_pending,
        'writer_applications_pending': writer_pending,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def dashboard_editor(request):
    """Editor-only dashboard. Writers and others are redirected to their own."""
    if _user_role(request.user) != 'editor':
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post, Review
    context = {
        'role': 'editor',
        'total_posts': Post.objects.count(),
        'published_posts': Post.objects.filter(status='published').count(),
        'total_reviews': Review.objects.count(),
        'draft_posts': Post.objects.filter(status='draft').count(),
        'recent_posts': Post.objects.order_by('-updated_at')[:5],
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def dashboard_writer(request):
    """Writer-only dashboard. Editors and others are redirected to their own."""
    if _user_role(request.user) != 'writer':
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post
    my_posts = Post.objects.filter(author=request.user)
    context = {
        'role': 'writer',
        'my_posts_count': my_posts.count(),
        'my_drafts': my_posts.filter(status='draft').count(),
        'my_published': my_posts.filter(status='published').count(),
        'recent_my_posts': my_posts.order_by('-updated_at')[:5],
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def profile(request):
    """View and edit profile. For readers, includes bookmarks/preferences links and apply to be a writer."""
    from content.models import PostLike, ReviewLike
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            if 'photo' in request.FILES:
                user_profile.photo = request.FILES['photo']
                user_profile.save(update_fields=['photo', 'updated_at'])
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    bookmarks_count = (
        BookmarkedPost.objects.filter(user=request.user).count()
        + BookmarkedReview.objects.filter(user=request.user).count()
        + BookmarkedNewsletterIssue.objects.filter(user=request.user).count()
    )
    liked_count = (
        PostLike.objects.filter(user=request.user).count()
        + ReviewLike.objects.filter(user=request.user).count()
    )
    prefs, _ = ReaderPreference.objects.get_or_create(user=request.user)
    followed_topics = int(prefs.follow_ai) + int(prefs.follow_startups) + int(prefs.follow_reviews)
    context = {
        'form': form,
        'user_role': _user_role(request.user),
        'profile_photo': user_profile.photo,
        'bookmarks_count': bookmarks_count,
        'liked_count': liked_count,
        'followed_topics': followed_topics,
    }
    if context['user_role'] == 'reader':
        context['writer_application_pending'] = WriterApplication.objects.filter(
            user=request.user, status=WriterApplication.STATUS_PENDING
        ).exists()
    if context['user_role'] == 'writer':
        context['editor_application_pending'] = EditorApplication.objects.filter(
            user=request.user, status=EditorApplication.STATUS_PENDING
        ).exists()
    return render(request, 'accounts/profile.html', context)


class ChangePasswordView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class ChangePasswordDoneView(PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'


# ----- Apply to be a writer (readers) / Review applications (admins) -----

@login_required
def writer_apply(request):
    """Readers can submit an application to become a writer. One pending per user."""
    role = _user_role(request.user)
    if role == 'writer' or role == 'editor' or role == 'admin':
        messages.info(request, 'You already have writer or editor access.')
        return redirect('accounts:dashboard')

    pending = WriterApplication.objects.filter(user=request.user, status=WriterApplication.STATUS_PENDING).first()
    if pending:
        messages.info(request, 'You already have a pending application. An admin will review it soon.')
        return render(request, 'accounts/writer_apply.html', {'application': pending, 'form': None})

    if request.method == 'POST':
        form = WriterApplicationForm(request.POST)
        if form.is_valid():
            WriterApplication.objects.create(
                user=request.user,
                message=form.cleaned_data.get('message', '').strip(),
                status=WriterApplication.STATUS_PENDING,
            )
            messages.success(request, 'Your application has been submitted. An admin will review it.')
            return redirect('reader:account_settings')
    else:
        form = WriterApplicationForm()
    return render(request, 'accounts/writer_apply.html', {'form': form, 'application': None})


@login_required
def writer_applications_list(request):
    """Admin: list all writer applications (pending first)."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    applications = WriterApplication.objects.select_related('user', 'reviewed_by').order_by('-created_at')
    pending_count = applications.filter(status=WriterApplication.STATUS_PENDING).count()
    return render(request, 'accounts/writer_applications.html', {
        'applications': applications,
        'pending_count': pending_count,
    })


@login_required
def writer_application_approve(request, pk):
    """Admin: approve application — add user to Writers group."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    application = get_object_or_404(WriterApplication, pk=pk)
    if application.status != WriterApplication.STATUS_PENDING:
        messages.warning(request, 'This application was already processed.')
        return redirect('accounts:writer_applications_list')

    writers, _ = Group.objects.get_or_create(name='Writers')
    application.user.groups.add(writers)
    application.status = WriterApplication.STATUS_APPROVED
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    messages.success(request, f'{application.user.get_username()} is now a writer.')
    return redirect('accounts:writer_applications_list')


@login_required
def writer_application_reject(request, pk):
    """Admin: reject application."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    application = get_object_or_404(WriterApplication, pk=pk)
    if application.status != WriterApplication.STATUS_PENDING:
        messages.warning(request, 'This application was already processed.')
        return redirect('accounts:writer_applications_list')

    application.status = WriterApplication.STATUS_REJECTED
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    messages.success(request, 'Application rejected.')
    return redirect('accounts:writer_applications_list')


# ----- Apply to be an editor (writers) / Review applications (admins) -----

@login_required
def editor_apply(request):
    """Writers can submit an application to become an editor. One pending per user."""
    role = _user_role(request.user)
    if role == 'editor' or role == 'admin':
        messages.info(request, 'You already have editor access.')
        return redirect('accounts:dashboard')
    if role != 'writer':
        messages.info(request, 'Only writers can apply to become an editor.')
        return redirect('accounts:dashboard')

    pending = EditorApplication.objects.filter(user=request.user, status=EditorApplication.STATUS_PENDING).first()
    if pending:
        messages.info(request, 'You already have a pending application. An admin will review it soon.')
        return render(request, 'accounts/editor_apply.html', {'application': pending, 'form': None})

    if request.method == 'POST':
        form = EditorApplicationForm(request.POST)
        if form.is_valid():
            EditorApplication.objects.create(
                user=request.user,
                message=form.cleaned_data.get('message', '').strip(),
                status=EditorApplication.STATUS_PENDING,
            )
            messages.success(request, 'Your application has been submitted. An admin will review it.')
            return redirect('accounts:dashboard_writer')
    else:
        form = EditorApplicationForm()
    return render(request, 'accounts/editor_apply.html', {'form': form, 'application': None})


@login_required
def editor_applications_list(request):
    """Admin: list all editor applications (pending first)."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    applications = EditorApplication.objects.select_related('user', 'reviewed_by').order_by(
        '-created_at'
    )
    pending_count = applications.filter(status=EditorApplication.STATUS_PENDING).count()
    return render(request, 'accounts/editor_applications.html', {
        'applications': applications,
        'pending_count': pending_count,
    })


@login_required
def editor_application_approve(request, pk):
    """Admin: approve application — add user to Editors group."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    application = get_object_or_404(EditorApplication, pk=pk)
    if application.status != EditorApplication.STATUS_PENDING:
        messages.warning(request, 'This application was already processed.')
        return redirect('accounts:editor_applications_list')

    editors, _ = Group.objects.get_or_create(name='Editors')
    application.user.groups.add(editors)
    application.status = EditorApplication.STATUS_APPROVED
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    messages.success(request, f'{application.user.get_username()} is now an editor.')
    return redirect('accounts:editor_applications_list')


@login_required
def editor_application_reject(request, pk):
    """Admin: reject application."""
    if _user_role(request.user) != 'admin':
        return _redirect_to_role_dashboard(request.user)
    application = get_object_or_404(EditorApplication, pk=pk)
    if application.status != EditorApplication.STATUS_PENDING:
        messages.warning(request, 'This application was already processed.')
        return redirect('accounts:editor_applications_list')

    application.status = EditorApplication.STATUS_REJECTED
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save()
    messages.success(request, 'Application rejected.')
    return redirect('accounts:editor_applications_list')


# ----- Review drafts: editors/admins publish or reject writers' drafts -----

def _user_can_review_drafts(user):
    """Editors and admins can review and publish/reject drafts."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Editors').exists()
    )


@login_required
def review_drafts(request):
    """List draft posts and reviews for editors/admins to publish or reject."""
    if not _user_can_review_drafts(request.user):
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post, Review
    draft_posts = Post.objects.filter(status='draft').select_related('author', 'category').order_by('-updated_at')
    draft_reviews = Review.objects.filter(status='draft').select_related('author').order_by('-updated_at')
    return render(request, 'accounts/review_drafts.html', {
        'draft_posts': draft_posts,
        'draft_reviews': draft_reviews,
    })


@login_required
def review_drafts_publish_post(request, pk):
    """Approve and publish a draft post. Editors cannot publish their own; only another editor or admin can."""
    if not _user_can_review_drafts(request.user):
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post
    post = get_object_or_404(Post, pk=pk)
    if post.status != 'draft':
        messages.warning(request, 'This post is already published.')
        return redirect('accounts:review_drafts')
    if not request.user.is_superuser and post.author_id == request.user.pk:
        messages.error(request, 'You cannot publish your own content. Another editor or admin must approve it.')
        return redirect('accounts:review_drafts')
    post.status = 'published'
    post.published_by = request.user
    post.save()
    messages.success(request, f'"{post.title}" is now published.')
    return redirect('accounts:review_drafts')


@login_required
def review_drafts_reject_post(request, pk):
    """Reject a draft post — leave as draft (editor/admin only)."""
    if not _user_can_review_drafts(request.user):
        return _redirect_to_role_dashboard(request.user)
    from content.models import Post
    post = get_object_or_404(Post, pk=pk)
    messages.info(request, f'"{post.title}" left as draft. Writer can edit and resubmit.')
    return redirect('accounts:review_drafts')


@login_required
def review_drafts_publish_review(request, pk):
    """Approve and publish a draft review. Editors cannot publish their own; only another editor or admin can."""
    if not _user_can_review_drafts(request.user):
        return _redirect_to_role_dashboard(request.user)
    from content.models import Review
    review = get_object_or_404(Review, pk=pk)
    if review.status != 'draft':
        messages.warning(request, 'This review is already published.')
        return redirect('accounts:review_drafts')
    if not request.user.is_superuser and review.author_id == request.user.pk:
        messages.error(request, 'You cannot publish your own content. Another editor or admin must approve it.')
        return redirect('accounts:review_drafts')
    review.status = 'published'
    review.published_by = request.user
    review.save()
    messages.success(request, f'"{review.title}" is now published.')
    return redirect('accounts:review_drafts')


@login_required
def review_drafts_reject_review(request, pk):
    """Reject a draft review — leave as draft (editor/admin only)."""
    if not _user_can_review_drafts(request.user):
        return _redirect_to_role_dashboard(request.user)
    from content.models import Review
    review = get_object_or_404(Review, pk=pk)
    messages.info(request, f'"{review.title}" left as draft. Writer can edit and resubmit.')
    return redirect('accounts:review_drafts')


# ----- User management (admin only, in-site) -----

@login_required
def user_list(request):
    """List all users (admin/superuser only)."""
    if not request.user.is_superuser:
        return redirect('accounts:dashboard')
    from django.core.paginator import Paginator
    users = User.objects.all().order_by('-date_joined')
    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/user_list.html', {'page_obj': page_obj})


@login_required
def user_edit(request, pk):
    """Edit a user: profile, is_active, groups (admin only)."""
    if not request.user.is_superuser:
        return redirect('accounts:dashboard')
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated.')
            return redirect('accounts:user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'accounts/user_edit.html', {'form': form, 'edit_user': user})


# ----- Reader account: /account/settings, /account/liked, /account/bookmarks, /account/preferences -----

@login_required
def account_settings(request):
    """Settings hub: profile, liked posts, bookmarks, preferences, password."""
    from content.models import PostLike, ReviewLike
    bookmarks_count = (
        BookmarkedPost.objects.filter(user=request.user).count()
        + BookmarkedReview.objects.filter(user=request.user).count()
        + BookmarkedNewsletterIssue.objects.filter(user=request.user).count()
    )
    liked_count = (
        PostLike.objects.filter(user=request.user).count()
        + ReviewLike.objects.filter(user=request.user).count()
    )
    prefs, _ = ReaderPreference.objects.get_or_create(user=request.user)
    context = {
        'bookmarks_count': bookmarks_count,
        'liked_count': liked_count,
        'prefs': prefs,
        'user_role': _user_role(request.user),
    }
    if context['user_role'] == 'reader':
        context['writer_application_pending'] = WriterApplication.objects.filter(
            user=request.user, status=WriterApplication.STATUS_PENDING
        ).exists()
    return render(request, 'accounts/account_settings.html', context)


@login_required
def account_liked_posts(request):
    """List of articles the user has liked."""
    from content.models import PostLike, ReviewLike
    from django.utils import timezone
    selected_type = request.GET.get('type', 'articles')
    if selected_type not in {'articles', 'reviews', 'newsletters'}:
        selected_type = 'articles'
    # Posts the user liked (only published), ordered by when they liked (newest first)
    liked = PostLike.objects.filter(
        user=request.user,
        post__status='published',
        post__published_at__isnull=False,
        post__published_at__lte=timezone.now(),
    ).select_related('post', 'post__category').order_by('-created_at')
    liked_reviews = ReviewLike.objects.filter(
        user=request.user,
        review__status='published',
        review__published_at__isnull=False,
        review__published_at__lte=timezone.now(),
    ).select_related('review').order_by('-created_at')
    return render(request, 'accounts/account_liked_posts.html', {
        'liked_list': liked,
        'liked_reviews': liked_reviews,
        'selected_type': selected_type,
    })


@login_required
def account_bookmarks(request):
    """List of saved articles, reviews, and newsletter issues."""
    selected_type = request.GET.get('type', 'articles')
    if selected_type not in {'articles', 'reviews', 'newsletters'}:
        selected_type = 'articles'
    bookmarks = BookmarkedPost.objects.filter(user=request.user).select_related('post').order_by('-created_at')
    bookmarked_reviews = BookmarkedReview.objects.filter(user=request.user).select_related('review').order_by('-created_at')
    bookmarked_newsletters = BookmarkedNewsletterIssue.objects.filter(
        user=request.user
    ).select_related('newsletter_issue').order_by('-created_at')
    return render(request, 'accounts/account_bookmarks.html', {
        'bookmarks': bookmarks,
        'bookmarked_reviews': bookmarked_reviews,
        'bookmarked_newsletters': bookmarked_newsletters,
        'selected_type': selected_type,
    })


@login_required
def account_preferences(request):
    """Reader preferences: topics (AI, Startups, Reviews), weekly newsletter."""
    prefs, _ = ReaderPreference.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        prefs.follow_ai = 'follow_ai' in request.POST
        prefs.follow_startups = 'follow_startups' in request.POST
        prefs.follow_reviews = 'follow_reviews' in request.POST
        prefs.newsletter_weekly = 'newsletter_weekly' in request.POST
        prefs.save()
        messages.success(request, 'Preferences saved.')
        return redirect('reader:account_preferences')
    return render(request, 'accounts/account_preferences.html', {'prefs': prefs})


@login_required
def toggle_save_article(request, pk):
    """Save or remove article from bookmarks. JSON for AJAX (no redirect, no flash message)."""
    from content.models import Post
    post = get_object_or_404(Post, pk=pk)
    ajax = _inline_toggle_ajax(request)
    bp = BookmarkedPost.objects.filter(user=request.user, post=post).first()
    if bp:
        bp.delete()
        saved = False
        if not ajax:
            messages.success(request, 'Article removed from your bookmarks.')
    else:
        BookmarkedPost.objects.get_or_create(user=request.user, post=post)
        saved = True
        if not ajax:
            messages.success(request, 'Article saved. View it in your bookmarks.')
    if ajax:
        from content.views import display_save_public

        real_save_count = BookmarkedPost.objects.filter(post=post).count()
        save_count = display_save_public(real_save_count, post.pk, 'post')
        return JsonResponse({'ok': True, 'saved': saved, 'save_count': save_count})
    next_url = request.GET.get('next') or request.POST.get('next') or post.get_absolute_url()
    return redirect(next_url)


@login_required
def toggle_save_review(request, pk):
    """Save or remove review from bookmarks. JSON for AJAX (no redirect)."""
    from content.models import Review
    review = get_object_or_404(Review, pk=pk)
    ajax = _inline_toggle_ajax(request)
    br = BookmarkedReview.objects.filter(user=request.user, review=review).first()
    if br:
        br.delete()
        saved = False
        if not ajax:
            messages.success(request, 'Review removed from your bookmarks.')
    else:
        BookmarkedReview.objects.get_or_create(user=request.user, review=review)
        saved = True
        if not ajax:
            messages.success(request, 'Review saved. View it in your bookmarks.')
    if ajax:
        from content.views import display_save_public

        real_save_count = BookmarkedReview.objects.filter(review=review).count()
        save_count = display_save_public(real_save_count, review.pk, 'review')
        return JsonResponse({'ok': True, 'saved': saved, 'save_count': save_count})
    next_url = request.GET.get('next') or request.POST.get('next') or review.get_absolute_url()
    return redirect(next_url)


@login_required
def toggle_save_newsletter(request, pk):
    """Save or remove newsletter issue from bookmarks. JSON for AJAX (no redirect)."""
    from content.models import NewsletterIssue
    issue = get_object_or_404(NewsletterIssue, pk=pk)
    ajax = _inline_toggle_ajax(request)
    bn = BookmarkedNewsletterIssue.objects.filter(user=request.user, newsletter_issue=issue).first()
    if bn:
        bn.delete()
        saved = False
        if not ajax:
            messages.success(request, 'Newsletter removed from your bookmarks.')
    else:
        BookmarkedNewsletterIssue.objects.get_or_create(user=request.user, newsletter_issue=issue)
        saved = True
        if not ajax:
            messages.success(request, 'Newsletter saved. View it in your bookmarks.')
    if ajax:
        from content.views import display_save_public

        real_save_count = BookmarkedNewsletterIssue.objects.filter(newsletter_issue=issue).count()
        save_count = display_save_public(real_save_count, issue.pk, 'newsletter')
        return JsonResponse({'ok': True, 'saved': saved, 'save_count': save_count})
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('content:newsletter_issue_detail', kwargs={'pk': issue.pk})
    return redirect(next_url)
