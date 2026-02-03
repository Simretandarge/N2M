"""
Account forms: signup, profile edit.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class SignUpForm(UserCreationForm):
    """Registration form: username, email, password, and optional Writer role."""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
    )
    account_type = forms.ChoiceField(
        required=True,
        initial='reader',
        choices=[
            ('reader', 'Reader — I just want to read and follow'),
            ('writer', 'Writer — I want to contribute articles/reviews'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Editors are assigned by the team; you can request Writer access here.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'account_type')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
        # Move account_type after password2 for display order
        self.field_order = ['username', 'email', 'password1', 'password2', 'account_type']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            account_type = self.cleaned_data.get('account_type')
            if account_type == 'writer':
                from django.contrib.auth.models import Group
                writers, _ = Group.objects.get_or_create(name='Writers')
                user.groups.add(writers)
                user.is_staff = True  # Required to access Django admin (to create posts)
                user.save(update_fields=['is_staff'])
        return user


class EditorApplicationForm(forms.Form):
    """Writer applies to become an editor (optional message)."""
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Tell us why you\'d like to become an editor (optional).',
            'rows': 4,
        }),
        label='Message (optional)',
    )


class ProfileForm(forms.ModelForm):
    """Edit profile: username, email, first_name, last_name."""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
