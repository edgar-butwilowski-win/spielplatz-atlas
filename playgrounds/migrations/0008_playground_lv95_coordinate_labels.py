# Generated manually for SpielplatzAtlas

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playgrounds', '0007_playground_uuid_and_sync_coordinates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playground',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name='LV95 Y'),
        ),
        migrations.AlterField(
            model_name='playground',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True, verbose_name='LV95 X'),
        ),
    ]
