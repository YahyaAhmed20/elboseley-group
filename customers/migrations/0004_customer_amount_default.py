from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('customers','0003_customer_phone')]
    operations=[migrations.AlterField(model_name='customer',name='amount',field=models.DecimalField(decimal_places=2,default=0,max_digits=12,verbose_name='المبلغ'))]
