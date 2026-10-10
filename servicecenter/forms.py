from django import forms
from django.utils import timezone
from customers.models import Customer
from payroll.models import Employee
from .models import Device, RepairOrder

class DeviceForm(forms.ModelForm):
    class Meta:
        model=Device
        fields=['customer','device_type','description']
        widgets={'device_type':forms.TextInput(attrs={'placeholder':'مثال: موبايل / لابتوب / تكييف'}),'description':forms.Textarea(attrs={'rows':2})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['customer'].queryset=Customer.objects.all().order_by('name')

class RepairReceiveForm(forms.Form):
    customer=forms.ModelChoiceField(queryset=Customer.objects.all().order_by('name'),empty_label='— اختر العميل —')
    existing_device=forms.ModelChoiceField(queryset=Device.objects.none(),required=False,empty_label='— جهاز جديد —',label='الجهاز السابق')
    device_type=forms.CharField(max_length=120,required=False,label='نوع الجهاز')
    device_description=forms.CharField(required=False,label='وصف الجهاز',widget=forms.Textarea(attrs={'rows':2}))
    fault_description=forms.CharField(label='وصف العطل',widget=forms.Textarea(attrs={'rows':3}))
    deposit=forms.DecimalField(min_value=0,decimal_places=2,max_digits=12,label='العربون',widget=forms.NumberInput(attrs={'step':'0.01'}))
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['deposit'].initial=0
        self.fields['existing_device'].queryset=Device.objects.select_related('customer').order_by('-created_at')
        if self.data.get('customer'):
            try:self.fields['existing_device'].queryset=Device.objects.filter(customer_id=self.data.get('customer')).order_by('-created_at')
            except (TypeError,ValueError):pass

    def clean(self):
        cleaned = super().clean()
        device = cleaned.get('existing_device'); customer = cleaned.get('customer')
        if device and customer and device.customer_id != customer.id:
            self.add_error('existing_device', 'الجهاز السابق لا يتبع هذا العميل.')
        if not device and not cleaned.get('device_type'):
            self.add_error('device_type', 'اكتب نوع الجهاز للجهاز الجديد.')
        return cleaned

class RepairWorkForm(forms.ModelForm):
    class Meta:
        model=RepairOrder
        fields=['employee','repair_notes','cost','labor','status']
        widgets={'repair_notes':forms.Textarea(attrs={'rows':3}),'cost':forms.NumberInput(attrs={'step':'0.01','min':'0'}),'labor':forms.NumberInput(attrs={'step':'0.01','min':'0'})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['employee'].queryset=Employee.objects.filter(status=Employee.Status.ACTIVE); self.fields['employee'].required=True

class RepairFilterForm(forms.Form):
    q=forms.CharField(required=False,label='بحث')
    status=forms.ChoiceField(required=False,choices=[('', 'كل الحالات')]+list(RepairOrder.Status.choices))
    employee=forms.ModelChoiceField(required=False,queryset=Employee.objects.filter(status=Employee.Status.ACTIVE),empty_label='كل الموظفين')
