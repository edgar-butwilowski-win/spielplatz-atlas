# Robust transition migration for moving defect planning data to MaintenanceAction.
# The committed historic migrations are older than the current model state, so this
# migration intentionally works through database introspection instead of relying on
# a complete Django migration state for all current models.

from django.db import migrations


DEFECT_TABLE = "inspections_defect"
MAINTENANCE_TABLE = "inspections_maintenanceaction"
ASSIGNMENT_TABLE = "notifications_defectassignment"


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


def drop_column_if_exists(schema_editor, table_name, column_name):
    connection = schema_editor.connection
    if not column_exists(connection, table_name, column_name):
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {quote(connection, table_name)} DROP COLUMN {quote(connection, column_name)}")
    except Exception:
        # Keeping the old database column is safe because the Django model no longer
        # maps it. Some older SQLite versions cannot drop columns in-place.
        pass


def migrate_planning_to_maintenance_actions(apps, schema_editor):
    connection = schema_editor.connection
    if not table_exists(connection, DEFECT_TABLE) or not table_exists(connection, MAINTENANCE_TABLE):
        return

    add_column_if_missing(schema_editor, MAINTENANCE_TABLE, "assigned_to_id", "bigint NULL")

    if not column_exists(connection, DEFECT_TABLE, "planned_resolution_date"):
        return

    assignments = {}
    if table_exists(connection, ASSIGNMENT_TABLE) and column_exists(connection, ASSIGNMENT_TABLE, "assigned_to_id"):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT defect_id, assigned_to_id FROM {quote(connection, ASSIGNMENT_TABLE)} WHERE assigned_to_id IS NOT NULL"
            )
            assignments = {defect_id: assigned_to_id for defect_id, assigned_to_id in cursor.fetchall()}

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, planned_resolution_date FROM {quote(connection, DEFECT_TABLE)} WHERE planned_resolution_date IS NOT NULL"
        )
        planned_defects = cursor.fetchall()

    now_sql = "CURRENT_TIMESTAMP"
    for defect_id, planned_date in planned_defects:
        assigned_to_id = assignments.get(defect_id)
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT id FROM {quote(connection, MAINTENANCE_TABLE)} "
                "WHERE defect_id = %s AND status IN (%s, %s) "
                "ORDER BY planned_date ASC, created_at DESC LIMIT 1",
                [defect_id, "planned", "in_progress"],
            )
            row = cursor.fetchone()

        if row:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {quote(connection, MAINTENANCE_TABLE)} "
                    "SET planned_date = %s, assigned_to_id = %s, updated_at = " + now_sql + " "
                    "WHERE id = %s",
                    [planned_date, assigned_to_id, row[0]],
                )
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"INSERT INTO {quote(connection, MAINTENANCE_TABLE)} "
                    "(defect_id, title, description, assigned_to_id, planned_date, completed_date, status, public_visible, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, " + now_sql + ", " + now_sql + ")",
                    [defect_id, "Mangel beheben", "", assigned_to_id, planned_date, "planned", False],
                )

    drop_column_if_exists(schema_editor, DEFECT_TABLE, "planned_resolution_date")


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0021_remove_defect_in_progress_status"),
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(migrate_planning_to_maintenance_actions, reverse_noop),
    ]
