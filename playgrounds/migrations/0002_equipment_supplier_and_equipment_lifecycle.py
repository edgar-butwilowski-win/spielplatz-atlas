# Generated manually for SpielplatzAtlas

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playgrounds', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentSupplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Erstellt am')),
                ('organization', models.ForeignKey(blank=True, help_text='Leer bedeutet: global nutzbarer Lieferant.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='equipment_suppliers', to='tenants.organization', verbose_name='Organisation')),
            ],
            options={
                'verbose_name': 'Lieferant',
                'verbose_name_plural': 'Lieferanten',
                'ordering': ['name'],
                'unique_together': {('organization', 'name')},
            },
        ),
        migrations.AddField(
            model_name='playequipment',
            name='build_date',
            field=models.DateField(blank=True, null=True, verbose_name='Baudatum'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='demolition_date',
            field=models.DateField(blank=True, null=True, verbose_name='Abbruchdatum'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='norm',
            field=models.CharField(blank=True, max_length=200, verbose_name='Norm'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='not_inspectable',
            field=models.BooleanField(default=False, verbose_name='Nicht prüfbar'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='not_inspectable_reason',
            field=models.CharField(blank=True, max_length=500, verbose_name='Grund nicht prüfbar'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='recommended_renovation_year',
            field=models.PositiveIntegerField(blank=True, help_text='Vierstellige Jahreszahl. Das Jahr darf nicht in der Vergangenheit liegen.', null=True, verbose_name='Empfohlenes Sanierungsjahr'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='renovation_comment',
            field=models.CharField(blank=True, max_length=500, verbose_name='Kommentar zur Sanierung'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='renovation_type',
            field=models.CharField(blank=True, choices=[('total', 'Totalsanierung'), ('partial', 'Teilsanierung')], max_length=20, verbose_name='Sanierungsart'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='sequence_number',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Laufnummer'),
        ),
        migrations.AddField(
            model_name='playequipment',
            name='supplier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipment', to='playgrounds.equipmentsupplier', verbose_name='Lieferant'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='equipment_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipment', to='playgrounds.equipmenttype', verbose_name='Spielgeräteart'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='inventory_number',
            field=models.CharField(blank=True, max_length=100, verbose_name='Inventar-Nr.'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktiv'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='manufacturer',
            field=models.CharField(blank=True, max_length=150, verbose_name='Hersteller'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='name',
            field=models.CharField(max_length=200, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='playground',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment', to='playgrounds.playground', verbose_name='Spielplatz'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='public_visible',
            field=models.BooleanField(default=True, verbose_name='Öffentlich sichtbar'),
        ),
        migrations.AlterField(
            model_name='playequipment',
            name='year_built',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Baujahr'),
        ),
    ]
