
from django.db import migrations


def create_supplier_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "CREATE SEQUENCE IF NOT EXISTS supplier_supplier_code_seq"
        )
        cursor.execute(
            """
            SELECT setval(
                'supplier_supplier_code_seq',
                COALESCE(MAX(code), 1),
                MAX(code) IS NOT NULL
            )
            FROM supplier_supplier
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("supplier", "0003_supplier_code"),
    ]

    operations = [
        migrations.RunPython(
            create_supplier_sequence,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
