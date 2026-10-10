from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('payroll','0002_rename_payroll_emp_name_0c5b7d_idx_payroll_emp_name_748290_idx_and_more')]
    operations=[
        migrations.AddField(model_name='employee',name='phone',field=models.CharField(default='',max_length=50,verbose_name='رقم الهاتف')),
        migrations.AddField(model_name='employee',name='national_id',field=models.CharField(default='',max_length=30,verbose_name='رقم البطاقة')),
        migrations.AlterField(model_name='employee',name='name',field=models.CharField(max_length=150,verbose_name='اسم الموظف')),
    ]
