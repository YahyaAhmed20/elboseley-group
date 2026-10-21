
from django.db import migrations


def create_customer_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "CREATE SEQUENCE IF NOT EXISTS customers_customer_code_seq"
        )
        cursor.execute(
            """
            SELECT setval(
                'customers_customer_code_seq',
                COALESCE(MAX(code), 1),
                MAX(code) IS NOT NULL
            )
            FROM customers_customer
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0005_remove_customer_customers_phone_idx_customer_code_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_customer_sequence,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
