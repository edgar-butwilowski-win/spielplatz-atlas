from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    ROLE_READER = "reader"
    ROLE_INSPECTOR = "inspector"
    ROLE_ORG_ADMIN = "org_admin"

    ROLE_CHOICES = (
        (ROLE_READER, "Lesender interner User"),
        (ROLE_INSPECTOR, "Kontrolleur/in"),
        (ROLE_ORG_ADMIN, "Organisations-Admin"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Benutzer",
    )

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="user_profiles",
        verbose_name="Organisation",
    )

    role = models.CharField(
        "Rolle",
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_READER,
        help_text="Die Rolle ist die Quelle der fachlichen Berechtigungen.",
    )

    is_active_for_organization = models.BooleanField(
        "Aktiv für Organisation",
        default=True,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        label = self.user.get_full_name().strip() or self.user.email or "Benutzer ohne E-Mail"
        return f"{label} – {self.organization}"

    @property
    def may_manage_organization(self):
        return self.is_active_for_organization and self.role == self.ROLE_ORG_ADMIN

    @property
    def may_view_internal(self):
        return self.is_active_for_organization and self.role in {
            self.ROLE_READER,
            self.ROLE_INSPECTOR,
            self.ROLE_ORG_ADMIN,
        }

    @property
    def may_inspect(self):
        return self.is_active_for_organization and self.role in {
            self.ROLE_INSPECTOR,
            self.ROLE_ORG_ADMIN,
        }

    @property
    def may_maintain(self):
        return self.is_active_for_organization and self.role in {
            self.ROLE_INSPECTOR,
            self.ROLE_ORG_ADMIN,
        }
