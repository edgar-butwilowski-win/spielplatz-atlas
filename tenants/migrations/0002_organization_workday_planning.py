from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="workday_monday",
            field=models.BooleanField(default=True, verbose_name="Montag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_tuesday",
            field=models.BooleanField(default=True, verbose_name="Dienstag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_wednesday",
            field=models.BooleanField(default=True, verbose_name="Mittwoch"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_thursday",
            field=models.BooleanField(default=True, verbose_name="Donnerstag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_friday",
            field=models.BooleanField(default=True, verbose_name="Freitag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_saturday",
            field=models.BooleanField(default=False, verbose_name="Samstag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="workday_sunday",
            field=models.BooleanField(default=False, verbose_name="Sonntag"),
        ),
        migrations.AddField(
            model_name="organization",
            name="planning_lead_time_workdays",
            field=models.PositiveSmallIntegerField(
                default=7,
                help_text="Anzahl Arbeitstage, die das Planungsdatum standardmässig vor dem Fälligkeitsdatum liegen soll.",
                verbose_name="Planungsdatum: Arbeitstage vor Fälligkeit",
            ),
        ),
    ]
