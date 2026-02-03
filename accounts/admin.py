"""
Register EditorApplication in Django admin (optional; admins can also use the Editor applications page).
"""
from django.contrib import admin
from .models import EditorApplication


@admin.register(EditorApplication)
class EditorApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('user__username', 'message')
    readonly_fields = ('user', 'message', 'created_at')
