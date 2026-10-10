from django.db import migrations

def seed(apps,schema_editor):
    Category=apps.get_model('expenses','ExpenseCategory')
    for name in ['مرتبات','كهربا','نت','نظافة','أخرى']:
        Category.objects.get_or_create(name=name)

def unseed(apps,schema_editor):
    Category=apps.get_model('expenses','ExpenseCategory'); Category.objects.filter(name__in=['مرتبات','كهربا','نت','نظافة','أخرى']).delete()

class Migration(migrations.Migration):
    dependencies=[('expenses','0001_initial')]
    operations=[migrations.RunPython(seed,unseed)]
