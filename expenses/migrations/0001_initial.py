from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator
from decimal import Decimal
class Migration(migrations.Migration):
    initial=True
    dependencies=[('payroll','0003_employee_identity'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name='ExpenseCategory',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('name',models.CharField(max_length=100,unique=True,verbose_name='البند')),('is_active',models.BooleanField(default=True))],options={'ordering':['name']}),
        migrations.CreateModel(name='Expense',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('amount',models.DecimalField(decimal_places=2,max_digits=12,validators=[MinValueValidator(Decimal('0.01'))],verbose_name='التكلفة')),('expense_date',models.DateField(verbose_name='التاريخ')),('note',models.TextField(blank=True,verbose_name='ملاحظة')),('created_at',models.DateTimeField(auto_now_add=True)),('beneficiary',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='expenses',to='payroll.employee')),('category',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='expenses',to='expenses.expensecategory')),('created_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to=settings.AUTH_USER_MODEL))],options={'ordering':['-expense_date','-created_at'],'indexes':[models.Index(fields=['expense_date'],name='expenses_date_idx'),models.Index(fields=['beneficiary','category'],name='expenses_benef_idx')]})
    ]
