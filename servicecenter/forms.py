from django import forms
from django.utils import timezone
from customers.models import Customer
from payroll.models import Employee
from .models import Device, RepairOrder


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['customer', 'device_type', 'description']
        widgets = {
            'device_type': forms.TextInput(attrs={'placeholder': 'مثال: موبايل / لابتوب / تكييف'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('name')


class RepairReceiveForm(forms.Form):
    customer = forms.CharField(
        label='العميل / رقم الهاتف',
        widget=forms.TextInput(attrs={
            'id': 'customer-search',
            'autocomplete': 'off',
            'placeholder': 'اكتب اسم العميل أو رقم الهاتف',
        }),
    )

    customer_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'customer-id'}),
    )

    existing_device = forms.CharField(
        required=False,
        label='الجهاز السابق',
        widget=forms.TextInput(attrs={
            'id': 'device-search',
            'autocomplete': 'off',
            'placeholder': 'ابحث بكود الجهاز أو نوعه',
        }),
    )

    existing_device_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'device-id'}),
    )

    device_type = forms.CharField(
        max_length=120,
        required=False,
        label='نوع الجهاز',
    )

    device_description = forms.CharField(
        required=False,
        label='وصف الجهاز',
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    fault_description = forms.CharField(
        label='وصف العطل',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    deposit = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        max_digits=12,
        label='العربون',
        widget=forms.NumberInput(attrs={'step': '0.01'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['deposit'].initial = 0

        customer_id = (
            self.data.get('customer_id')
            or self.initial.get('customer_id')
            or self.initial.get('customer')
        )

        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                self.fields['customer'].initial = (
                    f'{customer.name} - {customer.phone or ""}'
                )
                self.fields['customer_id'].initial = customer.pk
            except (Customer.DoesNotExist, TypeError, ValueError):
                pass

        device_id = (
            self.data.get('existing_device_id')
            or self.initial.get('existing_device_id')
        )

        if device_id:
            try:
                device = Device.objects.select_related('customer').get(pk=device_id)
                self.fields['existing_device'].initial = (
                    f'#{device.code} - {device.device_type}'
                )
                self.fields['existing_device_id'].initial = device.pk
            except (Device.DoesNotExist, TypeError, ValueError):
                pass

    def clean(self):
        cleaned = super().clean()

        customer_id = cleaned.get('customer_id')
        customer = None

        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                self.add_error('customer_id', 'العميل المختار غير موجود.')

        if not customer:
            self.add_error('customer', 'اختر عميلًا من نتائج البحث.')

        device = None
        device_id = cleaned.get('existing_device_id')

        if device_id:
            try:
                device = Device.objects.select_related('customer').get(
                    pk=device_id
                )
            except Device.DoesNotExist:
                self.add_error(
                    'existing_device_id',
                    'الجهاز المختار غير موجود.',
                )

        if device and customer and device.customer_id != customer.pk:
            self.add_error(
                'existing_device',
                'الجهاز السابق لا يتبع هذا العميل.',
            )
            device = None

        if not device and not cleaned.get('device_type'):
            self.add_error(
                'device_type',
                'اكتب نوع الجهاز للجهاز الجديد.',
            )

        cleaned['customer'] = customer
        cleaned['existing_device'] = device

        return cleaned


class RepairWorkForm(forms.ModelForm):
    class Meta:
        model = RepairOrder
        fields = ['employee', 'repair_notes', 'cost', 'labor', 'status']
        widgets = {
            'repair_notes': forms.Textarea(attrs={'rows': 3}),
            'cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'labor': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status=Employee.Status.ACTIVE)
        self.fields['employee'].required = True


class RepairFilterForm(forms.Form):
    q = forms.CharField(required=False, label='بحث')
    status = forms.ChoiceField(required=False, choices=[('', 'كل الحالات')] + list(RepairOrder.Status.choices))
    employee = forms.ModelChoiceField(required=False, queryset=Employee.objects.filter(status=Employee.Status.ACTIVE), empty_label='كل الموظفين')