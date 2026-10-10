from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('customers','0002_rename_customers_c_name_4d7b3f_idx_customers_c_name_f018e2_idx_and_more')]
    operations=[
        migrations.AddField(model_name='customer',name='phone',field=models.CharField(default='',max_length=50,verbose_name='رقم الهاتف')),
        migrations.AlterField(model_name='customer',name='personal_number',field=models.CharField(blank=True,default='',max_length=100,verbose_name='الرقم الشخصي')),
        migrations.AlterField(model_name='customer',name='car_number',field=models.CharField(blank=True,default='',max_length=100,verbose_name='رقم العربية')),
        migrations.AddIndex(model_name='customer',index=models.Index(fields=['phone'],name='customers_phone_idx')),
    ]
