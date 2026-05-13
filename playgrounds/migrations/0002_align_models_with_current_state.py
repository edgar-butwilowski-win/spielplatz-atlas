# Generated manually for SpielplatzAtlas

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0001_initial"),
        ("media_assets", "0002_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="playequipment",
            options={
                "ordering": ["playground__name", "sequence_number", "name"],
                "verbose_name": "Spielgerät",
                "verbose_name_plural": "Spielgeräte",
            },
        ),
        migrations.AlterField(
            model_name="equipmenttype",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="Leer bedeutet: globale Standard-Spielgeräteart.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="equipment_types",
                to="tenants.organization",
                verbose_name="Organisation",
            ),
        ),
        migrations.AlterField(
            model_name="equipmenttype",
            name="name",
            field=models.CharField("Name", max_length=200),
        ),
        migrations.AlterField(
            model_name="equipmenttype",
            name="code",
            field=models.CharField("Code", blank=True, max_length=80),
        ),
        migrations.AlterField(
            model_name="equipmenttype",
            name="norm_reference",
            field=models.CharField(
                "Norm-/Quellenhinweis",
                blank=True,
                help_text="Zum Beispiel: SN EN 1176, SN EN 1177 oder gerätespezifische Referenz.",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="equipmenttype",
            name="is_active",
            field=models.BooleanField("Aktiv", default=True),
        ),
        migrations.AddField(
            model_name="equipmenttype",
            name="is_standard",
            field=models.BooleanField(
                "Standardwert",
                default=False,
                help_text="Ja, wenn dieser Eintrag Teil des globalen App-Standardkatalogs ist.",
            ),
        ),
        migrations.AddField(
            model_name="equipmenttype",
            name="standard_version",
            field=models.CharField(
                "Standardversion",
                blank=True,
                help_text="Version des Standardkatalogs, z. B. SN-EN-1176-1177-v1.",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="equipmenttype",
            name="source_note",
            field=models.TextField("Interner Quellen-/Bearbeitungshinweis", blank=True),
        ),
        migrations.AddField(
            model_name="equipmenttype",
            name="is_locked",
            field=models.BooleanField(
                "Gesperrt",
                default=False,
                help_text="Gesperrte Standardwerte können nur durch Super-Admins geändert werden.",
            ),
        ),
        migrations.CreateModel(
            name="EquipmentSupplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField("Name", max_length=200)),
                ("is_active", models.BooleanField("Aktiv", default=True)),
                ("created_at", models.DateTimeField("Erstellt am", auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="Leer bedeutet: global nutzbarer Lieferant.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="equipment_suppliers",
                        to="tenants.organization",
                        verbose_name="Organisation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lieferant",
                "verbose_name_plural": "Lieferanten",
                "ordering": ["name"],
                "unique_together": {("organization", "name")},
            },
        ),
        migrations.AlterField(
            model_name="playground",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="playgrounds",
                to="tenants.organization",
                verbose_name="Organisation",
            ),
        ),
        migrations.AddField(
            model_name="playground",
            name="uuid",
            field=models.UUIDField(
                "UUID",
                default=uuid.uuid4,
                help_text="Eindeutige UUID des Spielplatzes. Beim Webservice-Abgleich wird darüber synchronisiert.",
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="playground",
            name="name",
            field=models.CharField("Name", max_length=200),
        ),
        migrations.AlterField(
            model_name="playground",
            name="slug",
            field=models.SlugField("URL-Kürzel", max_length=100),
        ),
        migrations.AddField(
            model_name="playground",
            name="number",
            field=models.IntegerField("Nummer", blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="playground",
            name="address",
            field=models.CharField("Adresse", blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="playground",
            name="street_name",
            field=models.CharField("Strassenname", blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="playground",
            name="house_number",
            field=models.CharField("Hausnummer", blank=True, max_length=40),
        ),
        migrations.AlterField(
            model_name="playground",
            name="district",
            field=models.CharField("Quartier", blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="playground",
            name="latitude",
            field=models.DecimalField("LV95 Y", blank=True, decimal_places=8, max_digits=16, null=True),
        ),
        migrations.AlterField(
            model_name="playground",
            name="longitude",
            field=models.DecimalField("LV95 X", blank=True, decimal_places=8, max_digits=16, null=True),
        ),
        migrations.AlterField(
            model_name="playground",
            name="description",
            field=models.TextField("Beschrieb", blank=True),
        ),
        migrations.AddField(
            model_name="playground",
            name="construction_costs",
            field=models.FloatField("Erstellungskosten", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playground",
            name="inspection_suspended_from",
            field=models.DateField("Inspektion aussetzen von", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playground",
            name="inspection_suspended_until",
            field=models.DateField("Inspektion aussetzen bis", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playground",
            name="photo",
            field=models.ForeignKey(
                blank=True,
                help_text="Optionales Hauptfoto des Spielplatzes.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="playgrounds",
                to="media_assets.imageasset",
                verbose_name="Foto",
            ),
        ),
        migrations.AlterField(
            model_name="playground",
            name="is_active",
            field=models.BooleanField("Aktiv", default=True),
        ),
        migrations.AlterField(
            model_name="playground",
            name="public_visible",
            field=models.BooleanField("Öffentlich", default=True),
        ),
        migrations.AlterField(
            model_name="playground",
            name="created_at",
            field=models.DateTimeField("Erstellt am", auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="playground",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="equipment",
                to="playgrounds.playground",
                verbose_name="Spielplatz",
            ),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="equipment_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="equipment",
                to="playgrounds.equipmenttype",
                verbose_name="Spielgeräteart",
            ),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="name",
            field=models.CharField("Name", max_length=200),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="sequence_number",
            field=models.PositiveIntegerField("Laufnummer", blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="inventory_number",
            field=models.CharField("Inventar-Nr.", blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="manufacturer",
            field=models.CharField("Hersteller", blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="supplier",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="equipment",
                to="playgrounds.equipmentsupplier",
                verbose_name="Lieferant",
            ),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="norm",
            field=models.CharField("Norm", blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="year_built",
            field=models.PositiveIntegerField("Baujahr", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="build_date",
            field=models.DateField("Baudatum", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="demolition_date",
            field=models.DateField("Abbruchdatum", blank=True, null=True),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="renovation_type",
            field=models.CharField(
                "Sanierungsart",
                blank=True,
                choices=[("total", "Totalsanierung"), ("partial", "Teilsanierung")],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="recommended_renovation_year",
            field=models.PositiveIntegerField(
                "Empfohlenes Sanierungsjahr",
                blank=True,
                help_text="Vierstellige Jahreszahl. Das Jahr darf nicht in der Vergangenheit liegen.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="renovation_comment",
            field=models.CharField("Kommentar zur Sanierung", blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="not_inspectable",
            field=models.BooleanField("Nicht prüfbar", default=False),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="not_inspectable_reason",
            field=models.CharField("Grund nicht prüfbar", blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="latitude",
            field=models.DecimalField("Breitengrad", blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="longitude",
            field=models.DecimalField("Längengrad", blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="public_visible",
            field=models.BooleanField("Öffentlich sichtbar", default=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="is_active",
            field=models.BooleanField("Aktiv", default=True),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="photo",
            field=models.ForeignKey(
                blank=True,
                help_text="Optionales Hauptfoto dieses Spielgeräts.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="play_equipment",
                to="media_assets.imageasset",
                verbose_name="Foto",
            ),
        ),
        migrations.AlterField(
            model_name="playequipment",
            name="created_at",
            field=models.DateTimeField("Erstellt am", auto_now_add=True),
        ),
        migrations.CreateModel(
            name="PlaygroundSurface",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField("Name", max_length=200)),
                (
                    "surface_type",
                    models.CharField(
                        "Belagsart",
                        choices=[
                            ("sand", "Sand"),
                            ("gravel", "Rundkies / Fallschutzkies"),
                            ("wood_chips", "Holzschnitzel"),
                            ("bark", "Rindenmulch"),
                            ("rubber", "Fallschutzbelag"),
                            ("grass", "Rasen"),
                            ("other", "Sonstiger Belag"),
                        ],
                        default="other",
                        max_length=50,
                    ),
                ),
                ("description", models.TextField("Beschreibung", blank=True)),
                ("public_visible", models.BooleanField("Öffentlich sichtbar", default=True)),
                ("is_active", models.BooleanField("Aktiv", default=True)),
                ("created_at", models.DateTimeField("Erstellt am", auto_now_add=True)),
                (
                    "playground",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="surfaces",
                        to="playgrounds.playground",
                        verbose_name="Spielplatz",
                    ),
                ),
            ],
            options={
                "verbose_name": "Fallschutzfläche / Boden",
                "verbose_name_plural": "Fallschutzflächen / Böden",
                "ordering": ["playground__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="PlaygroundAccessory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField("Name", max_length=200)),
                (
                    "accessory_type",
                    models.CharField(
                        "Ausstattungsart",
                        choices=[
                            ("bench", "Sitzbank"),
                            ("waste_bin", "Abfalleimer"),
                            ("fence", "Zaun"),
                            ("gate", "Tor"),
                            ("sign", "Beschilderung"),
                            ("lighting", "Beleuchtung"),
                            ("table", "Tisch"),
                            ("shade", "Sonnenschutz"),
                            ("other", "Sonstige Ausstattung"),
                        ],
                        default="other",
                        max_length=50,
                    ),
                ),
                ("description", models.TextField("Beschreibung", blank=True)),
                ("public_visible", models.BooleanField("Öffentlich sichtbar", default=True)),
                ("is_active", models.BooleanField("Aktiv", default=True)),
                ("created_at", models.DateTimeField("Erstellt am", auto_now_add=True)),
                (
                    "playground",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="accessories",
                        to="playgrounds.playground",
                        verbose_name="Spielplatz",
                    ),
                ),
            ],
            options={
                "verbose_name": "Zusatzausstattung",
                "verbose_name_plural": "Zusatzausstattung",
                "ordering": ["playground__name", "name"],
            },
        ),
    ]
