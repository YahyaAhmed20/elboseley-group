from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='اسم العامل')),
                ('salary', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='المرتب الشهري')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='تاريخ بداية العمل')),
                ('status', models.CharField(choices=[('active', 'يعمل'), ('inactive', 'متوقف')], default='active', max_length=10, verbose_name='الحالة')),
                ('notes', models.TextField(blank=True, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='PayrollMonth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField(verbose_name='السنة')),
                ('month', models.PositiveSmallIntegerField(verbose_name='الشهر')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-year', '-month']},
        ),
        migrations.CreateModel(
            name='EmployeePayroll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('salary', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='مرتب الشهر')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payrolls', to='payroll.employee')),
                ('payroll_month', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employee_payrolls', to='payroll.payrollmonth')),
            ],
            options={'ordering': ['employee__name']},
        ),
        migrations.CreateModel(
            name='PayrollTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('advance', 'سلفة'), ('waste', 'هدر'), ('other', 'خصم آخر')], max_length=10, verbose_name='النوع')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='المبلغ')),
                ('note', models.TextField(blank=True, verbose_name='الملاحظة')),
                ('transaction_date', models.DateField(verbose_name='التاريخ')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('employee_payroll', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='payroll.employeepayroll')),
            ],
            options={'ordering': ['-transaction_date', '-created_at']},
        ),
        migrations.AddIndex(model_name='employee', index=models.Index(fields=['name'], name='payroll_emp_name_0c5b7d_idx')),
        migrations.AddIndex(model_name='employee', index=models.Index(fields=['status'], name='payroll_emp_status_7bdb2d_idx')),
        migrations.AddConstraint(model_name='payrollmonth', constraint=models.UniqueConstraint(fields=('year', 'month'), name='unique_payroll_month')),
        migrations.AddConstraint(model_name='payrollmonth', constraint=models.CheckConstraint(condition=models.Q(('month__gte', 1), ('month__lte', 12)), name='valid_payroll_month')),
        migrations.AddConstraint(model_name='employeepayroll', constraint=models.UniqueConstraint(fields=('employee', 'payroll_month'), name='unique_employee_payroll_month')),
        migrations.AddIndex(model_name='employeepayroll', index=models.Index(fields=['payroll_month', 'employee'], name='payroll_empl_payroll_98b9a4_idx')),
        migrations.AddIndex(model_name='payrolltransaction', index=models.Index(fields=['employee_payroll', 'kind'], name='payroll_payr_employee_4f8a7a_idx')),
        migrations.AddIndex(model_name='payrolltransaction', index=models.Index(fields=['transaction_date'], name='payroll_payr_transact_2d4d6d_idx')),
    ]
