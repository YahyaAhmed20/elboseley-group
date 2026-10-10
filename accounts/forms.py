from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'role']
        labels = {
            'first_name': 'الاسم الكامل',
            'username':   'اسم المستخدم',
            'role':       'الصلاحية',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'محمد أحمد'}),
            'username':   forms.TextInput(attrs={'placeholder': 'mohamed123'}),
        }

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError('اسم المستخدم محجوز.')
        return u

    def clean_password(self):
        p = self.cleaned_data['password']
        validate_password(p)
        return p

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user