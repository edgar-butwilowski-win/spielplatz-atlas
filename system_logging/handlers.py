# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

import logging
from datetime import timedelta

from django.apps import apps
from django.db import DEFAULT_DB_ALIAS, OperationalError, ProgrammingError, connections
from django.utils import timezone


class DatabaseLogHandler(logging.Handler):
    """Django logging handler with console fallback until the database table exists."""

    table_available = None
    is_emitting = False
    last_cleanup_at = None

    def emit(self, record):
        if self.__class__.is_emitting:
            return

        try:
            self.__class__.is_emitting = True
            if self.can_write_to_database():
                self.write_to_database(record)
            else:
                self.emit_to_console(record)
        except Exception:
            self.handleError(record)
        finally:
            self.__class__.is_emitting = False

    def can_write_to_database(self):
        if not apps.ready:
            return False

        if self.__class__.table_available is True:
            return True

        try:
            LogEntry = apps.get_model("system_logging", "LogEntry")
            table_name = LogEntry._meta.db_table
            connection = connections[DEFAULT_DB_ALIAS]
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names(cursor)
        except (OperationalError, ProgrammingError):
            self.__class__.table_available = False
            return False
        except Exception:
            self.__class__.table_available = False
            return False

        self.__class__.table_available = table_name in table_names
        return self.__class__.table_available

    def write_to_database(self, record):
        LogEntry = apps.get_model("system_logging", "LogEntry")
        LogEntry.objects.create(
            level=record.levelname,
            logger_name=record.name,
            message=self.format(record),
            module=getattr(record, "module", "") or "",
            function_name=getattr(record, "funcName", "") or "",
            line_number=getattr(record, "lineno", None),
            pathname=getattr(record, "pathname", "") or "",
            process_id=getattr(record, "process", None),
            thread_id=getattr(record, "thread", None),
            exception_text=self.formatException(record.exc_info) if record.exc_info else "",
        )
        self.cleanup_old_entries(LogEntry)

    def cleanup_old_entries(self, LogEntry):
        now = timezone.now()
        if self.__class__.last_cleanup_at and now - self.__class__.last_cleanup_at < timedelta(hours=1):
            return
        LogEntry.objects.filter(created_at__lt=now - timedelta(days=365)).delete()
        self.__class__.last_cleanup_at = now

    def emit_to_console(self, record):
        print(f"{record.levelname} {record.name}: {self.format(record)}")
