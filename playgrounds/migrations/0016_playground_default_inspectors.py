from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("playgrounds", "0015_remove_playequipment_manufacturer"),
    ]

    operations = [
        migrations.AddField(
            model_name="playground",
            name="default_visual_inspector",
            field=models.ForeignKey(
                blank=True,
                help_text="Wird bei neuen visuellen Kontrollaufträgen automatisch voreingestellt.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_visual_playgrounds",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Default-Kontrolleur/in visuell",
            ),
        ),
        migrations.AddField(
            model_name="playground",
            name="default_operational_inspector",
            field=models.ForeignKey(
                blank=True,
                help_text="Wird bei neuen operativen Kontrollaufträgen automatisch voreingestellt.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_operational_playgrounds",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Default-Kontrolleur/in operativ",
            ),
        ),
        migrations.AddField(
            model_name="playground",
            name="default_annual_inspector",
            field=models.ForeignKey(
                blank=True,
                help_text="Wird bei neuen jährlichen Kontrollaufträgen automatisch voreingestellt.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_annual_playgrounds",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Default-Kontrolleur/in jährlich",
            ),
        ),
    ]
