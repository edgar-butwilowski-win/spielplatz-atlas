from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0010_alter_model_verbose_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipmentsupplier",
            name="tel_nr",
            field=models.CharField(blank=True, max_length=80, verbose_name="Telefonnummer"),
        ),
        migrations.AddField(
            model_name="equipmentsupplier",
            name="strasse",
            field=models.CharField(blank=True, max_length=80, verbose_name="Strasse"),
        ),
        migrations.AddField(
            model_name="equipmentsupplier",
            name="plz_ort",
            field=models.CharField(blank=True, max_length=80, verbose_name="PLZ / Ort"),
        ),
        migrations.AddField(
            model_name="equipmentsupplier",
            name="e_mail",
            field=models.EmailField(blank=True, max_length=80, verbose_name="E-Mail"),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE playgrounds_playequipment "
                "SET year_built = printf('%04d-01-01', CAST(year_built AS INTEGER)) "
                "WHERE year_built IS NOT NULL "
                "AND length(CAST(year_built AS TEXT)) = 4 "
                "AND CAST(year_built AS INTEGER) BETWEEN 1000 AND 9999"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="year_built",
            field=models.DateField(blank=True, null=True, verbose_name="Baujahr / Baudatum"),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="demolition_date",
            field=models.DateField(blank=True, null=True, verbose_name="Abbruchjahr / Abbruchdatum"),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="recommended_renovation_year",
            field=models.PositiveIntegerField(blank=True, help_text="Vierstellige Jahreszahl. Historische Legacy-Werte sind zulässig.", null=True, verbose_name="Empfohlenes Sanierungsjahr"),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="not_to_inspect",
            field=models.BooleanField(default=False, help_text="Administrative Prüfausnahme. Das Spielgerät bleibt im Bestand, wird aber nicht in Kontrollprotokollen berücksichtigt. Dieses Feld wird durch die Organisation verwaltet.", verbose_name="Nicht zu prüfen"),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="not_to_inspect_reason",
            field=models.CharField(blank=True, max_length=500, verbose_name="Grund nicht zu prüfen"),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="not_inspectable",
            field=models.BooleanField(default=False, help_text="Das Spielgerät muss grundsätzlich geprüft werden, konnte aber bei einer Kontrolle nicht geprüft werden, z. B. weil es nicht zugänglich war.", verbose_name="Nicht prüfbar"),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name="LV95 Y"),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name="LV95 X"),
        ),
    ]
