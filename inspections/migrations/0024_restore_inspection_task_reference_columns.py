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


def add_column_if_missing(schema_editor, table_name, column_name, ddl_fragment):
    connection = schema_editor.connection
    if not table_exists(connection, table_name) or column_exists(connection, table_name, column_name):
        return
    with connection.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {quote(connection, table_name)} ADD COLUMN {quote(connection, column_name)} {ddl_fragment}")


def restore_reference_columns(apps, schema_editor):
    add_column_if_missing(schema_editor, TASK_TABLE, "generated_from_inspection_id", "bigint NULL")
    add_column_if_missing(schema_editor, TASK_TABLE, "created_from_inspection_id", "bigint NULL")
    add_column_if_missing(schema_editor, TASK_TABLE, "completed_by_inspection_id", "bigint NULL")


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0023_restore_inspection_task_note"),
    ]

    operations = [
        migrations.RunPython(restore_reference_columns, reverse_noop),
    ]
