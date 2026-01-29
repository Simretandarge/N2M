"""
Django admin for content: draft/publish workflow, featured toggle.
Roles: Admin (full), Editor (publish/edit all), Writer (own drafts only).
"""
from django.contrib import admin
from .models import Category, Post, Review, NewsletterSubscriber


def user_is_writer(user):
    """User is in Writers group and not superuser."""
    return user.groups.filter(name='Writers').exists() and not user.is_superuser


def user_is_editor(user):
    """User is in Editors group (or superuser)."""
    return user.groups.filter(name='Editors').exists() or user.is_superuser


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if user_is_writer(request.user):
            # Writers can only view categories (for assigning to posts)
            return qs
        return qs

    def has_add_permission(self, request):
        # Only editors and admins can add categories
        return not user_is_writer(request.user) or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return not user_is_writer(request.user) or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return not user_is_writer(request.user) or request.user.is_superuser


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'is_featured', 'published_at', 'views')
    list_filter = ('status', 'is_featured', 'category')
    list_editable = ('status', 'is_featured')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('views', 'published_at', 'created_at', 'updated_at')
    date_hierarchy = 'published_at'
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'excerpt', 'content', 'featured_image')}),
        ('Organization', {'fields': ('category', 'author', 'is_featured')}),
        ('Publishing', {'fields': ('status', 'published_at', 'views')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if user_is_writer(request.user):
            return qs.filter(author=request.user)
        return qs

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if user_is_writer(request.user):
            # Writers cannot publish or set featured; cannot change author
            readonly = readonly + ['status', 'is_featured', 'published_at', 'author']
        return readonly

    def get_changelist_instance(self, request):
        # Writers cannot edit status/is_featured in list view
        if user_is_writer(request.user):
            self.list_editable = ()
        else:
            self.list_editable = ('status', 'is_featured')
        return super().get_changelist_instance(request)

    def save_model(self, request, obj, form, change):
        if not change and getattr(obj, 'author', None) is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'author' and user_is_writer(request.user):
            kwargs['disabled'] = True
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'product_name', 'status', 'rating', 'published_at')
    list_filter = ('status', 'rating')
    list_editable = ('status',)
    search_fields = ('title', 'product_name', 'summary', 'content')

    def get_changelist_instance(self, request):
        if user_is_writer(request.user):
            self.list_editable = ()
        else:
            self.list_editable = ('status',)
        return super().get_changelist_instance(request)

    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('published_at', 'created_at', 'updated_at')
    date_hierarchy = 'published_at'

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if user_is_writer(request.user):
            readonly = readonly + ['status', 'published_at', 'author']
        return readonly

    fieldsets = (
        (None, {'fields': ('title', 'slug', 'product_name', 'summary', 'content', 'featured_image')}),
        ('Review details', {'fields': ('rating', 'pros', 'cons')}),
        ('Organization', {'fields': ('author',)}),
        ('Publishing', {'fields': ('status', 'published_at')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if user_is_writer(request.user):
            return qs.filter(author=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if not change and getattr(obj, 'author', None) is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'author' and user_is_writer(request.user):
            kwargs['disabled'] = True
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if user_is_writer(request.user):
            # Writers can only view (if we give view permission); cannot add/change/delete
            return qs
        return qs

    def has_add_permission(self, request):
        return not user_is_writer(request.user) or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return not user_is_writer(request.user) or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return not user_is_writer(request.user) or request.user.is_superuser
