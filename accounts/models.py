from django.conf import settings
from django.db import models


class UserProfile(models.Model):
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

    is_active_for_organization = models.BooleanField(
        "Aktiv für Organisation",
        default=True,
    )

    is_org_admin = models.BooleanField(
        "Organisationsverwaltung",
        default=False,
        help_text="Darf Stammdaten und Einstellungen der eigenen Organisation verwalten.",
    )

    can_view_internal = models.BooleanField(
        "Interne Ansicht",
        default=True,
        help_text="Darf interne Daten der eigenen Organisation ansehen.",
    )

    can_inspect = models.BooleanField(
        "Kontrollen durchführen",
        default=False,
        help_text="Darf Kontrollen starten, Prüfantworten erfassen und Kontrollen abschliessen.",
    )

    can_maintain = models.BooleanField(
        "Mängel und Unterhalt bearbeiten",
        default=False,
        help_text="Darf Mängel und Instandhaltungsmassnahmen erfassen und bearbeiten.",
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        return f"{self.user} – {self.organization}"

    @property
    def may_manage_organization(self):
        return self.is_active_for_organization and self.is_org_admin

    @property
    def may_view_internal(self):
        return self.is_active_for_organization and (
            self.is_org_admin
            or self.can_view_internal
            or self.can_inspect
            or self.can_maintain
        )

    @property
    def may_inspect(self):
        return self.is_active_for_organization and (
            self.is_org_admin
            or self.can_inspect
        )

    @property
    def may_maintain(self):
        return self.is_active_for_organization and (
            self.is_org_admin
            or self.can_maintain
            or self.can_inspect
        )
