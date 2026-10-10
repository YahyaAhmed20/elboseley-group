from django.conf import settings
from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='اسم العميل')),
                ('personal_number', models.CharField(max_length=100, verbose_name='الرقم الشخصي')),
                ('car_number', models.CharField(max_length=100, verbose_name='رقم العربية')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='المبلغ')),
                ('note', models.TextField(blank=True, verbose_name='الشغل / الملاحظة')),
                ('follow_up_enabled', models.BooleanField(default=False, verbose_name='تذكير بعد 6 شهور')),
                ('follow_up_date', models.DateField(blank=True, null=True, verbose_name='موعد المراجعة')),
                ('reminder_sent_at', models.DateTimeField(blank=True, null=True, verbose_name='آخر تذكير مُرسل')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='customers_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['name'], name='customers_c_name_4d7b3f_idx'),
                    models.Index(fields=['personal_number'], name='customers_c_persona_6a4f11_idx'),
                    models.Index(fields=['car_number'], name='customers_c_car_num_1a2d91_idx'),
                    models.Index(fields=['follow_up_enabled', 'follow_up_date'], name='customers_c_follow_u_3d2d0c_idx'),
                ],
            },
        ),
    ]
