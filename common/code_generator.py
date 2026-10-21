from django.db import transaction
from django.db import connections
from django.db.models import Max


def next_code(sequence_name, using="default"):
    connection = connections[using]

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT nextval(%s)", [sequence_name])
            return cursor.fetchone()[0]

    # SQLite fallback for local development.
    model_map = {
        "customers_customer_code_seq": ("customers", "Customer"),
        "supplier_supplier_code_seq": ("supplier", "Supplier"),
    }

    try:
        app_label, model_name = model_map[sequence_name]
    except KeyError:
        raise ValueError(f"Unsupported sequence: {sequence_name}")

    from django.apps import apps

    model = apps.get_model(app_label, model_name)
    with transaction.atomic(using=using):
        last_code = (
            model.objects.using(using)
            .select_for_update()
            .aggregate(max_code=Max("code"))["max_code"]
        )
        return (last_code or 0) + 1
