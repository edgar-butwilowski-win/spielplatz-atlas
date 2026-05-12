# Generated manually for SpielplatzAtlas

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_default_inspection_rules(apps, schema_editor):
    Organization = apps.get_model('tenants', 'Organization')
    InspectionRule = apps.get_model('inspections', 'InspectionRule')

    default_intervals = {
        'visual': 7,
        'operational': 90,
        'annual': 365,
    }

    for organization in Organization.objects.all():
        for inspection_type, interval_days in default_intervals.items():
            InspectionRule.objects.get_or_create(
                organization=organization,
                inspection_type=inspection_type,
                defaults={
                    'interval_days': interval_days,
                    'applies_to_all_playgrounds': True,
                    'is_active': True,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0001_initial'),
        ('tenants', '0001_initial'),
        ('playgrounds', '0008_playground_lv95_coordinate_labels'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InspectionRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inspection_type', models.CharField(choices=[('visual', 'Visuelle Routinekontrolle'), ('operational', 'Operative Kontrolle'), ('annual', 'Jährliche Hauptinspektion')], max_length=30, verbose_name='Kontrollart')),
                ('interval_days', models.PositiveIntegerField(help_text='Intervall für die Kontrollplanung auf Basis von SN EN 1176/1177.', verbose_name='Intervall in Tagen')),
                ('applies_to_all_playgrounds', models.BooleanField(default=True, verbose_name='Gilt für alle Spielplätze')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktiv')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Erstellt am')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Aktualisiert am')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspection_rules', to='tenants.organization', verbose_name='Organisation')),
            ],
            options={
                'verbose_name': 'Kontrollregel',
                'verbose_name_plural': 'Kontrollregeln',
                'ordering': ['organization__name', 'inspection_type'],
                'unique_together': {('organization', 'inspection_type')},
            },
        ),
        migrations.CreateModel(
            name='InspectionTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inspection_type', models.CharField(choices=[('visual', 'Visuelle Routinekontrolle'), ('operational', 'Operative Kontrolle'), ('annual', 'Jährliche Hauptinspektion')], max_length=30, verbose_name='Kontrollart')),
                ('due_date', models.DateField(verbose_name='Fällig am')),
                ('planned_date', models.DateField(blank=True, null=True, verbose_name='Geplant am')),
                ('status', models.CharField(choices=[('open', 'Offen'), ('planned', 'Geplant'), ('completed', 'Erledigt'), ('overdue', 'Überfällig'), ('suspended', 'Ausgesetzt'), ('cancelled', 'Storniert')], default='open', max_length=30, verbose_name='Status')),
                ('source', models.CharField(choices=[('automatic', 'Automatisch'), ('manual', 'Manuell')], default='automatic', max_length=30, verbose_name='Quelle')),
                ('note', models.TextField(blank=True, verbose_name='Interne Bemerkung')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Erstellt am')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Aktualisiert am')),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_inspection_tasks', to=settings.AUTH_USER_MODEL, verbose_name='Zugewiesen an')),
                ('completed_by_inspection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='completed_planning_tasks', to='inspections.inspection', verbose_name='Erledigt durch Kontrolle')),
                ('created_from_inspection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_follow_up_tasks', to='inspections.inspection', verbose_name='Erzeugt aus Kontrolle')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspection_tasks', to='tenants.organization', verbose_name='Organisation')),
                ('playground', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inspection_tasks', to='playgrounds.playground', verbose_name='Spielplatz')),
            ],
            options={
                'verbose_name': 'Kontrollauftrag',
                'verbose_name_plural': 'Kontrollaufträge',
                'ordering': ['due_date', 'planned_date', 'playground__name'],
                'indexes': [
                    models.Index(fields=['organization', 'status', 'due_date'], name='inspection__organiz_3e0302_idx'),
                    models.Index(fields=['playground', 'inspection_type', 'status'], name='inspection__playgro_dfdc60_idx'),
                ],
            },
        ),
        migrations.RunPython(seed_default_inspection_rules, migrations.RunPython.noop),
    ]
