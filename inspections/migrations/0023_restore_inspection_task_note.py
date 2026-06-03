from django.db import migrations


TASK_TABLE = "inspections_inspectiontask"


def table_exists(connection, table_name):
    return table_name in connection.introspection.table_names()


def column_exists(connection, table_name, column_name):
    if not table_exists(connection, table_name):
        return False
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table_name)
    return any(column.name == column_name for column in columns)


def quote(connection, name):
    return connection.ops.quote_name(name)


def add_note_column(apps, schema_editor):
    connection = schema_editor.connection
    if not table_exists(connection, TASK_TABLE) or column_exists(connection, TASK_TABLE, "note"):
        return
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {quote(connection, TASK_TABLE)} ADD COLUMN {quote(connection, 'note')} text NOT NULL DEFAULT ''")


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0002_move_defect_planning_to_maintenance_action"),
    ]

    operations = [
        migrations.RunPython(add_note_column, reverse_noop),
    ]
