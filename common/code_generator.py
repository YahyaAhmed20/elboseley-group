from django.db import connections


def next_code(sequence_name, using="default"):
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [sequence_name])
        return cursor.fetchone()[0]
