"""
Register account models in Django admin.
"""
from django.contrib import admin
from .models import (
    WriterApplication,
    EditorApplication,
    BookmarkedPost,
    BookmarkedReview,
    BookmarkedNewsletterIssue,
    ReaderPreference,
    UserProfile,
)


@admin.register(BookmarkedPost)
class BookmarkedPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__title')


@admin.register(BookmarkedReview)
class BookmarkedReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'review', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'review__title')


@admin.register(BookmarkedNewsletterIssue)
class BookmarkedNewsletterIssueAdmin(admin.ModelAdmin):
    list_display = ('user', 'newsletter_issue', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'newsletter_issue__title')


@admin.register(ReaderPreference)
class ReaderPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'follow_ai', 'follow_startups', 'follow_reviews', 'newsletter_weekly', 'updated_at')
    list_filter = ('follow_ai', 'follow_startups', 'follow_reviews', 'newsletter_weekly')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    search_fields = ('user__username', 'user__email')


@admin.register(WriterApplication)
class WriterApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('user__username', 'message')
    readonly_fields = ('user', 'message', 'created_at')


@admin.register(EditorApplication)
class EditorApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('user__username', 'message')
    readonly_fields = ('user', 'message', 'created_at')
