from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'اسم العميل'}),
            'phone': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
        }
