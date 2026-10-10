from decimal import Decimal
from datetime import timedelta
from django import forms
from .models import Employee, PayrollTransaction


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'phone', 'national_id', 'salary', 'start_date', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'مثال: محمد أحمد'}),
            'phone': forms.TextInput(attrs={'placeholder': 'رقم الهاتف'}),
            'national_id': forms.TextInput(attrs={'placeholder': 'رقم البطاقة'}),
            'salary': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class PayrollTransactionForm(forms.ModelForm):
    def __init__(self, *args, payroll_month=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.payroll_month = payroll_month
        if payroll_month:
            default_date = payroll_month.created_at.date().replace(day=1)
            self.fields['transaction_date'].widget.attrs['max'] = (
                default_date.replace(day=28) + timedelta(days=4)
            ).replace(day=1) - timedelta(days=1)
            self.fields['transaction_date'].widget.attrs['min'] = default_date

    def clean_transaction_date(self):
        value = self.cleaned_data['transaction_date']
        if self.payroll_month and (value.year, value.month) != (self.payroll_month.year, self.payroll_month.month):
            raise forms.ValidationError('تاريخ العملية يجب أن يكون داخل شهر المرتب المحدد.')
        return value

    class Meta:
        model = PayrollTransaction
        fields = ['kind', 'amount', 'transaction_date', 'note']
        widgets = {
            'amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'transaction_date': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3, 'placeholder': 'مثال: سلفة منتصف الشهر / هدر خامة...'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= Decimal('0'):
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من صفر.')
        return amount
