from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Zeitpunkt")),
                ("level", models.CharField(choices=[("DEBUG", "DEBUG"), ("INFO", "INFO"), ("WARNING", "WARNING"), ("ERROR", "ERROR"), ("CRITICAL", "CRITICAL")], db_index=True, max_length=20, verbose_name="Level")),
                ("logger_name", models.CharField(db_index=True, max_length=255, verbose_name="Logger")),
                ("message", models.TextField(verbose_name="Meldung")),
                ("module", models.CharField(blank=True, max_length=255, verbose_name="Modul")),
                ("function_name", models.CharField(blank=True, max_length=255, verbose_name="Funktion")),
                ("line_number", models.PositiveIntegerField(blank=True, null=True, verbose_name="Zeile")),
                ("pathname", models.TextField(blank=True, verbose_name="Dateipfad")),
                ("process_id", models.PositiveIntegerField(blank=True, null=True, verbose_name="Prozess-ID")),
                ("thread_id", models.PositiveBigIntegerField(blank=True, null=True, verbose_name="Thread-ID")),
                ("exception_text", models.TextField(blank=True, verbose_name="Exception")),
            ],
            options={
                "verbose_name": "Logging-Meldung",
                "verbose_name_plural": "Logging",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["-created_at", "level"], name="syslog_created_level_idx"),
                    models.Index(fields=["logger_name", "-created_at"], name="syslog_logger_created_idx"),
                ],
            },
        ),
    ]
