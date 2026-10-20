
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("supplier", "0003_supplier_code"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE SEQUENCE IF NOT EXISTS supplier_supplier_code_seq;

                SELECT setval(
                    'supplier_supplier_code_seq',
                    COALESCE(MAX(code), 1),
                    MAX(code) IS NOT NULL
                )
                FROM supplier_supplier;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
