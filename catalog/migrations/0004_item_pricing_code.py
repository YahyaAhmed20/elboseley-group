from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('catalog','0003_alter_brand_is_active_alter_brand_name_and_more')]
    operations=[
        migrations.AddField(model_name='item',name='code',field=models.PositiveIntegerField(blank=True,null=True,unique=True,verbose_name='كود الصنف')),
        migrations.AddField(model_name='item',name='sale_price',field=models.DecimalField(decimal_places=2,default=0,max_digits=12,verbose_name='سعر البيع')),
        migrations.AddField(model_name='item',name='opening_balance',field=models.DecimalField(decimal_places=2,default=0,max_digits=12,verbose_name='رصيد أول المدة')),
        migrations.AddField(model_name='item',name='image',field=models.ImageField(blank=True,null=True,upload_to='items/',verbose_name='الصورة')),
    ]
