# Generated manually for the consolidated user administration.

import uuid

from django.db import migrations, models


ROLE_READER = "reader"
ROLE_INSPECTOR = "inspector"
ROLE_ORG_ADMIN = "org_admin"


def internal_username():
    return f"u_{uuid.uuid4().hex}"


def normalize_email(value):
    return (value or "").strip().lower()


def migrate_users_and_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")

    seen_emails = set()

    for user in User.objects.order_by("id"):
        email = normalize_email(user.email)

        if not email:
            email = f"user-{user.pk}@invalid.local"

        if email in seen_emails:
            local_part, separator, domain = email.partition("@")
            if separator:
                email = f"{local_part}+user{user.pk}@{domain}"
            else:
                email = f"user-{user.pk}@invalid.local"

        seen_emails.add(email)
        user.email = email
        user.username = internal_username()
        user.save(update_fields=["email", "username"])

    for profile in UserProfile.objects.select_related("user"):
        if profile.user.is_superuser:
            profile.delete()
            continue

        if getattr(profile, "is_org_admin", False):
            role = ROLE_ORG_ADMIN
        elif getattr(profile, "can_inspect", False):
            role = ROLE_INSPECTOR
        else:
            role = ROLE_READER

        profile.role = role
        profile.save(update_fields=["role"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_remove_userprofile_role_userprofile_can_inspect_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("reader", "Lesender interner User"),
                    ("inspector", "Kontrolleur/in"),
                    ("org_admin", "Organisations-Admin"),
                ],
                default="reader",
                help_text="Die Rolle ist die Quelle der fachlichen Berechtigungen.",
                max_length=30,
                verbose_name="Rolle",
            ),
        ),
        migrations.RunPython(migrate_users_and_profiles, noop_reverse),
        migrations.RemoveField(
            model_name="userprofile",
            name="is_org_admin",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="can_view_internal",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="can_inspect",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="can_maintain",
        ),
    ]
