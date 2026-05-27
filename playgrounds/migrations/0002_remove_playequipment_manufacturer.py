from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="playequipment",
            name="manufacturer",
        ),
    ]
