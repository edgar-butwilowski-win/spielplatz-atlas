# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.db import models


class LogEntry(models.Model):
    LEVEL_DEBUG = "DEBUG"
    LEVEL_INFO = "INFO"
    LEVEL_WARNING = "WARNING"
    LEVEL_ERROR = "ERROR"
    LEVEL_CRITICAL = "CRITICAL"

    LEVEL_CHOICES = [
        (LEVEL_DEBUG, "DEBUG"),
        (LEVEL_INFO, "INFO"),
        (LEVEL_WARNING, "WARNING"),
        (LEVEL_ERROR, "ERROR"),
        (LEVEL_CRITICAL, "CRITICAL"),
    ]

    created_at = models.DateTimeField("Zeitpunkt", auto_now_add=True, db_index=True)
    level = models.CharField("Level", max_length=20, choices=LEVEL_CHOICES, db_index=True)
    logger_name = models.CharField("Logger", max_length=255, db_index=True)
    message = models.TextField("Meldung")
    module = models.CharField("Modul", max_length=255, blank=True)
    function_name = models.CharField("Funktion", max_length=255, blank=True)
    line_number = models.PositiveIntegerField("Zeile", null=True, blank=True)
    pathname = models.TextField("Dateipfad", blank=True)
    process_id = models.PositiveIntegerField("Prozess-ID", null=True, blank=True)
    thread_id = models.PositiveBigIntegerField("Thread-ID", null=True, blank=True)
    exception_text = models.TextField("Exception", blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "level"], name="syslog_created_level_idx"),
            models.Index(fields=["logger_name", "-created_at"], name="syslog_logger_created_idx"),
        ]
        verbose_name = "Logging-Meldung"
        verbose_name_plural = "Logging"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M:%S} {self.level} {self.logger_name}: {self.message[:80]}"
