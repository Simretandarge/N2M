"""
Account URLs: signup, signin, logout, forgot password, profile.
"""
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.SignInView.as_view(), name='login'),
    path('logout/', views.SignOutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/editor/', views.dashboard_editor, name='dashboard_editor'),
    path('dashboard/writer/', views.dashboard_writer, name='dashboard_writer'),
    path('dashboard/reader/', views.dashboard_reader, name='dashboard_reader'),
    path('profile/', views.profile, name='profile'),
    path('password-reset/', views.ForgotPasswordView.as_view(), name='password_reset'),
    path('password-reset/done/', views.ForgotPasswordDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.ForgotPasswordConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.ForgotPasswordCompleteView.as_view(), name='password_reset_complete'),
    path('password-change/', views.ChangePasswordView.as_view(), name='password_change'),
    path('password-change/done/', views.ChangePasswordDoneView.as_view(), name='password_change_done'),
    path('editor/apply/', views.editor_apply, name='editor_apply'),
    path('editor/applications/', views.editor_applications_list, name='editor_applications_list'),
    path('editor/applications/<int:pk>/approve/', views.editor_application_approve, name='editor_application_approve'),
    path('editor/applications/<int:pk>/reject/', views.editor_application_reject, name='editor_application_reject'),
    path('review-drafts/', views.review_drafts, name='review_drafts'),
    path('review-drafts/post/<int:pk>/publish/', views.review_drafts_publish_post, name='review_drafts_publish_post'),
    path('review-drafts/post/<int:pk>/reject/', views.review_drafts_reject_post, name='review_drafts_reject_post'),
    path('review-drafts/review/<int:pk>/publish/', views.review_drafts_publish_review, name='review_drafts_publish_review'),
    path('review-drafts/review/<int:pk>/reject/', views.review_drafts_reject_review, name='review_drafts_reject_review'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
]
