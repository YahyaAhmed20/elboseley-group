from django.db import migrations, models
from django.core.validators import MinValueValidator
from decimal import Decimal
class Migration(migrations.Migration):
    initial=True
    dependencies=[]
    operations=[migrations.CreateModel(name='Supplier',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('name',models.CharField(max_length=150,verbose_name='اسم المورد')),('phone',models.CharField(blank=True,max_length=50,verbose_name='رقم الهاتف')),('opening_balance',models.DecimalField(decimal_places=2,default=0,max_digits=12,validators=[MinValueValidator(Decimal('0'))],verbose_name='رصيد أول المدة')),('is_active',models.BooleanField(default=True,verbose_name='مُفعّل')),('created_at',models.DateTimeField(auto_now_add=True))],options={'ordering':['name'],'indexes':[models.Index(fields=['name'],name='supplier_name_idx'),models.Index(fields=['phone'],name='supplier_phone_idx')]})]
