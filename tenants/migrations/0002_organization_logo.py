from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("media_assets", "0001_initial"),
        ("tenants", "0002_organization_workday_planning"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="logo",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="organization_logos", to="media_assets.imageasset"),
        ),
    ]
