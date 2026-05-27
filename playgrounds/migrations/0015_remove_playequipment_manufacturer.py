from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0014_align_quartier_geojson_field"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playequipment",
            name="manufacturer",
        ),
    ]
