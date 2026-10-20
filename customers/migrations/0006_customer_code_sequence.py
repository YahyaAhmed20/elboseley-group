
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0005_remove_customer_customers_phone_idx_customer_code_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE SEQUENCE IF NOT EXISTS customers_customer_code_seq;

                SELECT setval(
                    'customers_customer_code_seq',
                    COALESCE(MAX(code), 1),
                    MAX(code) IS NOT NULL
                )
                FROM customers_customer;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
