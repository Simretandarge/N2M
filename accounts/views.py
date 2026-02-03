"""
Account views: signup, login, logout, password reset, profile, role-based dashboard.
"""
from django.shortcuts import render, redirect, resolve_url, get_object_or_404
from django.contrib.auth import login
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

from .forms import SignUpForm, ProfileForm, EditorApplicationForm
from .models import EditorApplication


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
    """User registration."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created. Welcome!')
            return redirect('accounts:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


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
        return resolve_url('accounts:dashboard_reader')


class SignOutView(LogoutView):
    next_page = 'content:home'


class ForgotPasswordView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    success_url = reverse_lazy('accounts:password_reset_done')
    subject_template_name = 'accounts/password_reset_subject.txt'


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
    return redirect('accounts:dashboard_reader')


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
    context = {
        'role': 'admin',
        'total_posts': Post.objects.count(),
        'published_posts': Post.objects.filter(status='published').count(),
        'total_reviews': Review.objects.count(),
        'draft_posts': Post.objects.filter(status='draft').count(),
        'editor_applications_pending': editor_pending,
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
def dashboard_reader(request):
    """Reader dashboard (no Editor/Writer role)."""
    if _user_role(request.user) != 'reader':
        return _redirect_to_role_dashboard(request.user)
    return render(request, 'accounts/dashboard.html', {'role': 'reader'})


@login_required
def profile(request):
    """View and edit profile."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


class ChangePasswordView(PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class ChangePasswordDoneView(PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'


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
