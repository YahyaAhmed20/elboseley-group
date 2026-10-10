from django import forms
from django.utils import timezone
from .models import Expense, ExpenseCategory
from payroll.models import Employee

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['beneficiary', 'category', 'amount', 'expense_date', 'note']
        widgets = {'amount': forms.NumberInput(attrs={'step':'0.01','min':'0.01'}), 'expense_date': forms.DateInput(attrs={'type':'date'}), 'note': forms.Textarea(attrs={'rows':2})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['beneficiary'].queryset = Employee.objects.filter(status=Employee.Status.ACTIVE)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        self.fields['expense_date'].initial = timezone.localdate()
