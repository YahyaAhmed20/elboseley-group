from django import forms
from .models import Item

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['code', 'name', 'cost', 'sale_price', 'opening_balance', 'image', 'min_qty']
        widgets = {
            'code': forms.NumberInput(attrs={'min': '1', 'placeholder': 'اتركه فارغًا للتسلسل التلقائي'}),
            'name': forms.TextInput(attrs={'placeholder': 'اسم الصنف'}),
            'cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'sale_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'opening_balance': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'min_qty': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
