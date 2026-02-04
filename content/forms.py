"""
Forms: contact, newsletter signup, writer post/review create/edit.
"""
from django import forms
from .models import NewsletterSubscriber, Post, Category, Review


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
    """Newsletter signup form."""
    class Meta:
        model = NewsletterSubscriber
        fields = ('email',)
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email',
            }),
        }


class PostForm(forms.ModelForm):
    """Writer-facing post create/edit form (no status, is_featured, or author)."""
    class Meta:
        model = Post
        fields = ('title', 'slug', 'excerpt', 'content', 'featured_image', 'category')
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
            'featured_image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['slug'].required = False


class ReviewForm(forms.ModelForm):
    """Writer-facing review create/edit form (no status or author)."""
    class Meta:
        model = Review
        fields = ('title', 'slug', 'product_name', 'summary', 'content', 'rating', 'pros', 'cons', 'featured_image')
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
            'featured_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['rating'].required = False


# ----- Editor/Admin CMS forms (include status, is_featured for posts) -----

class PostFormEditor(forms.ModelForm):
    """Editor/Admin: post create/edit with status and featured toggle."""
    class Meta:
        model = Post
        fields = ('title', 'slug', 'excerpt', 'content', 'featured_image', 'category', 'status', 'is_featured')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (leave blank to auto-generate)'}),
            'excerpt': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Short excerpt', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Full content', 'rows': 14}),
            'featured_image': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['slug'].required = False


class ReviewFormEditor(forms.ModelForm):
    """Editor/Admin: review create/edit with status."""
    class Meta:
        model = Review
        fields = ('title', 'slug', 'product_name', 'summary', 'content', 'rating', 'pros', 'cons', 'featured_image', 'status')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Review title'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'URL slug (leave blank to auto-generate)'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product or service name'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 12}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'pros': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cons': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'featured_image': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['rating'].required = False


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
