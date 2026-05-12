# Generated manually for SpielplatzAtlas

import uuid

from django.db import migrations, models


def fill_missing_playground_uuids(apps, schema_editor):
    Playground = apps.get_model('playgrounds', 'Playground')

    for playground in Playground.objects.filter(uuid__isnull=True):
        playground.uuid = uuid.uuid4()
        playground.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('playgrounds', '0006_playground_more_master_data_and_inspection_pause'),
    ]

    operations = [
        migrations.AddField(
            model_name='playground',
            name='uuid',
            field=models.UUIDField(blank=True, help_text='Eindeutige UUID des Spielplatzes. Beim Webservice-Abgleich wird darüber synchronisiert.', null=True, verbose_name='UUID'),
        ),
        migrations.RunPython(fill_missing_playground_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='playground',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='Eindeutige UUID des Spielplatzes. Beim Webservice-Abgleich wird darüber synchronisiert.', unique=True, verbose_name='UUID'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name='Breitengrad / Y'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name='Längengrad / X'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='number',
            field=models.IntegerField(blank=True, null=True, verbose_name='Nummer'),
        ),
    ]
