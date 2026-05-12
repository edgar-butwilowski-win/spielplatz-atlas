# Generated manually for SpielplatzAtlas

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playgrounds', '0005_equipment_supplier_and_equipment_lifecycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='playground',
            name='construction_costs',
            field=models.FloatField(blank=True, null=True, verbose_name='Erstellungskosten'),
        ),
        migrations.AddField(
            model_name='playground',
            name='house_number',
            field=models.CharField(blank=True, max_length=40, verbose_name='Hausnummer'),
        ),
        migrations.AddField(
            model_name='playground',
            name='inspection_suspended_from',
            field=models.DateField(blank=True, null=True, verbose_name='Inspektion aussetzen von'),
        ),
        migrations.AddField(
            model_name='playground',
            name='inspection_suspended_until',
            field=models.DateField(blank=True, null=True, verbose_name='Inspektion aussetzen bis'),
        ),
        migrations.AddField(
            model_name='playground',
            name='number',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Nummer'),
        ),
        migrations.AddField(
            model_name='playground',
            name='street_name',
            field=models.CharField(blank=True, max_length=200, verbose_name='Strassenname'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='description',
            field=models.TextField(blank=True, verbose_name='Beschrieb'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='public_visible',
            field=models.BooleanField(default=True, verbose_name='Öffentlich'),
        ),
    ]
