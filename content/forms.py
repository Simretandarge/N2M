"""
Forms: contact, newsletter signup, writer post/review create/edit.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import NewsletterSubscriber, NewsletterIssue, Post, Category, Review, PostComment, ReviewComment

MAX_UPLOAD_MB = 6
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_UPLOAD_ITEMS = 6


def _validate_max_file_size(uploaded_file, field_label='File'):
    """Validate uploaded file size with a shared 6 MB cap."""
    if uploaded_file and getattr(uploaded_file, 'size', 0) > MAX_UPLOAD_BYTES:
        raise ValidationError(f'{field_label} must be {MAX_UPLOAD_MB} MB or smaller.')
    return uploaded_file


def _validate_upload_list_size(files, field_label='Files'):
    if len(files) > MAX_UPLOAD_ITEMS:
        raise ValidationError(f'{field_label}: upload up to {MAX_UPLOAD_ITEMS} files at a time.')
    return files


class MultipleFileInput(forms.FileInput):
    """Multi-file field. Django 5+ blocks ``multiple`` on plain FileInput/ClearableFileInput unless this flag is set."""
    allow_multiple_selected = True


class MultipleUploadedFilesField(forms.Field):
    """
    Accept zero or more uploads from a multi-file input.

    Do not use ``FileField`` here: with ``allow_multiple_selected``, the widget
    returns a **list**; ``FileField.to_python`` expects one file and raises
    "No file was submitted. Check the encoding type on the form."
    """
    widget = MultipleFileInput

    def __init__(self, *, required=False, **kwargs):
        kwargs.setdefault('required', required)
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]
        out = []
        for f in value:
            if f in self.empty_values:
                continue
            if not hasattr(f, 'read'):
                raise ValidationError(
                    'Invalid file upload.',
                    code='invalid',
                )
            name = getattr(f, 'name', '') or ''
            if not name:
                continue
            out.append(f)
        return out

    def validate(self, value):
        super().validate(value)
        if self.required and not value:
            raise ValidationError(self.error_messages['required'], code='required')


class ContactForm(forms.Form):
    """Simple contact form (no model; can wire to email later)."""
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Your name',
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Your email',
    }))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Subject',
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control', 'placeholder': 'Your message', 'rows': 5,
    }))


class NewsletterForm(forms.ModelForm):
    """Newsletter signup form: weekly digest only."""
    class Meta:
        model = NewsletterSubscriber
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your email',
            }),
        }


class PostCommentForm(forms.ModelForm):
    """Comment on a post."""
    class Meta:
        model = PostComment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write a comment...',
                'rows': 2,
                'maxlength': 2000,
            }),
        }


class ReviewCommentForm(forms.ModelForm):
    """Comment on a review."""
    class Meta:
        model = ReviewComment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write a comment...',
                'rows': 2,
                'maxlength': 2000,
            }),
        }


class PostForm(forms.ModelForm):
    """Writer-facing post create/edit form (no status, is_featured, or author)."""
    class Meta:
        model = Post
        fields = ('title', 'slug', 'excerpt', 'content', 'featured_image', 'featured_video', 'category', 'instagram_post_url')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Post title',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL slug (leave blank to auto-generate)',
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Short excerpt for listings',
                'rows': 3,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Full content',
                'rows': 14,
            }),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'featured_video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'instagram_post_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.instagram.com/p/… or /reel/… (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['slug'].required = False
        self.fields['instagram_post_url'].required = False
        self.fields['extra_images'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional images.',
        )
        self.fields['extra_videos'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional videos.',
        )

    def clean_featured_image(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_image'), 'Featured image')

    def clean_featured_video(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_video'), 'Featured video')

    def clean_extra_images(self):
        files = list(self.cleaned_data.get('extra_images') or [])
        _validate_upload_list_size(files, 'Additional images')
        for f in files:
            _validate_max_file_size(f, 'Additional image')
        return files

    def clean_extra_videos(self):
        files = list(self.cleaned_data.get('extra_videos') or [])
        _validate_upload_list_size(files, 'Additional videos')
        for f in files:
            _validate_max_file_size(f, 'Additional video')
        return files


class ReviewForm(forms.ModelForm):
    """Writer-facing review create/edit form (no status or author)."""
    class Meta:
        model = Review
        fields = ('title', 'slug', 'product_name', 'summary', 'content', 'rating', 'pros', 'cons', 'featured_image', 'featured_video', 'instagram_post_url')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Review title',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'URL slug (leave blank to auto-generate)',
            }),
            'product_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product or service name',
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Short summary',
                'rows': 3,
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Full review content',
                'rows': 12,
            }),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1–5 (optional)',
                'min': 1,
                'max': 5,
            }),
            'pros': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'One pro per line or comma-separated',
                'rows': 3,
            }),
            'cons': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'One con per line or comma-separated',
                'rows': 3,
            }),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'featured_video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'instagram_post_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.instagram.com/p/… or /reel/… (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['rating'].required = False
        self.fields['instagram_post_url'].required = False
        self.fields['extra_images'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional images.',
        )
        self.fields['extra_videos'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional videos.',
        )

    def clean_featured_image(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_image'), 'Featured image')

    def clean_featured_video(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_video'), 'Featured video')

    def clean_extra_images(self):
        files = list(self.cleaned_data.get('extra_images') or [])
        _validate_upload_list_size(files, 'Additional images')
        for f in files:
            _validate_max_file_size(f, 'Additional image')
        return files

    def clean_extra_videos(self):
        files = list(self.cleaned_data.get('extra_videos') or [])
        _validate_upload_list_size(files, 'Additional videos')
        for f in files:
            _validate_max_file_size(f, 'Additional video')
        return files


# ----- Editor/Admin CMS forms (include status, is_featured for posts) -----

class PostFormEditor(forms.ModelForm):
    """Editor/Admin: post create/edit with status and featured toggle."""
    class Meta:
        model = Post
        fields = ('title', 'slug', 'excerpt', 'content', 'featured_image', 'featured_video', 'category', 'status', 'is_featured', 'instagram_post_url')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (leave blank to auto-generate)'}),
            'excerpt': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Short excerpt', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Full content', 'rows': 14}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'featured_video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'instagram_post_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.instagram.com/p/… or /reel/… (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['slug'].required = False
        self.fields['instagram_post_url'].required = False
        self.fields['extra_images'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional images.',
        )
        self.fields['extra_videos'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional videos.',
        )

    def clean_featured_image(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_image'), 'Featured image')

    def clean_featured_video(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_video'), 'Featured video')

    def clean_extra_images(self):
        files = list(self.cleaned_data.get('extra_images') or [])
        _validate_upload_list_size(files, 'Additional images')
        for f in files:
            _validate_max_file_size(f, 'Additional image')
        return files

    def clean_extra_videos(self):
        files = list(self.cleaned_data.get('extra_videos') or [])
        _validate_upload_list_size(files, 'Additional videos')
        for f in files:
            _validate_max_file_size(f, 'Additional video')
        return files


class ReviewFormEditor(forms.ModelForm):
    """Editor/Admin: review create/edit with status."""
    class Meta:
        model = Review
        fields = ('title', 'slug', 'product_name', 'summary', 'content', 'rating', 'pros', 'cons', 'featured_image', 'featured_video', 'status', 'instagram_post_url')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review title'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (leave blank to auto-generate)'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product or service name'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'pros': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cons': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'featured_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'featured_video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'instagram_post_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.instagram.com/p/… or /reel/… (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['rating'].required = False
        self.fields['instagram_post_url'].required = False
        self.fields['extra_images'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional images.',
        )
        self.fields['extra_videos'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional videos.',
        )

    def clean_featured_image(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_image'), 'Featured image')

    def clean_featured_video(self):
        return _validate_max_file_size(self.cleaned_data.get('featured_video'), 'Featured video')

    def clean_extra_images(self):
        files = list(self.cleaned_data.get('extra_images') or [])
        _validate_upload_list_size(files, 'Additional images')
        for f in files:
            _validate_max_file_size(f, 'Additional image')
        return files

    def clean_extra_videos(self):
        files = list(self.cleaned_data.get('extra_videos') or [])
        _validate_upload_list_size(files, 'Additional videos')
        for f in files:
            _validate_max_file_size(f, 'Additional video')
        return files


class CategoryForm(forms.ModelForm):
    """Category create/edit (editor/admin)."""
    class Meta:
        model = Category
        fields = ('name', 'slug')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (leave blank to auto-generate)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False


class NewsletterIssueForm(forms.ModelForm):
    """Create or edit a newsletter issue (title + content). Sent via Send action."""
    class Meta:
        model = NewsletterIssue
        fields = ('title', 'content', 'hero_image', 'hero_video')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Daily digest — 4 Feb 2025'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 14, 'placeholder': 'Plain text or HTML. Body of the email sent to subscribers.'}),
            'hero_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'hero_video': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_hero_image(self):
        return _validate_max_file_size(self.cleaned_data.get('hero_image'), 'Hero image')

    def clean_hero_video(self):
        return _validate_max_file_size(self.cleaned_data.get('hero_video'), 'Hero video')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['extra_images'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional images.',
        )
        self.fields['extra_videos'] = MultipleUploadedFilesField(
            required=False,
            widget=MultipleFileInput(attrs={'class': 'form-control'}),
            help_text=f'Optional: upload up to {MAX_UPLOAD_ITEMS} additional videos.',
        )

    def clean_extra_images(self):
        files = list(self.cleaned_data.get('extra_images') or [])
        _validate_upload_list_size(files, 'Additional images')
        for f in files:
            _validate_max_file_size(f, 'Additional image')
        return files

    def clean_extra_videos(self):
        files = list(self.cleaned_data.get('extra_videos') or [])
        _validate_upload_list_size(files, 'Additional videos')
        for f in files:
            _validate_max_file_size(f, 'Additional video')
        return files
