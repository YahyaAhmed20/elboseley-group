from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('catalog','0004_item_pricing_code')]
    operations=[
        migrations.AlterField(model_name='item',name='type',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='catalog.itemtype')),
        migrations.AlterField(model_name='item',name='unit',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='catalog.unit')),
    ]
