# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import UserProfile
from accounts.permissions import get_user_organization, user_may_manage_organization
from inspections.planning import rebuild_planning_for_organization

from .models import Organization, OrganizationRegistrationRequest


@admin.action(
    description=(
        "Kontrollplanung neu berechnen – erstellt fehlende und aktualisiert offene "
        "Kontrollaufträge; abgeschlossene Aufträge bleiben unverändert."
    )
)
def rebuild_inspection_planning_for_organizations(modeladmin, request, queryset):
    total_created = 0
    total_updated = 0
    total_unchanged = 0
    processed_count = 0

    for organization in queryset:
        result = rebuild_planning_for_organization(organization)
        processed_count += 1
        total_created += result["created"]
        total_updated += result["updated"]
        total_unchanged += result["unchanged"]

        modeladmin.message_user(
            request,
            (
                f"Kontrollplanung für '{organization.name}' neu berechnet. "
                f"Erstellt: {result['created']}, aktualisiert: {result['updated']}, "
                f"unverändert: {result['unchanged']}."
            ),
            level=messages.SUCCESS,
        )

    if processed_count:
        modeladmin.message_user(
            request,
            (
                f"{processed_count} Organisation(en) verarbeitet. "
                f"Gesamt erstellt: {total_created}, aktualisiert: {total_updated}, "
                f"unverändert: {total_unchanged}."
            ),
            level=messages.SUCCESS,
        )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "is_public",
        "primary_color",
        "secondary_color",
        "created_at",
    )
    list_filter = ("is_active", "is_public")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    actions = (rebuild_inspection_planning_for_organizations,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(id=organization.id)

        return qs.none()

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "name",
                "slug",
                "is_active",
                "is_public",
                "primary_color",
                "secondary_color",
                "logo",
            )

        return (
            "name",
            "primary_color",
            "secondary_color",
            "logo",
        )

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()

        return ("name",)

    def has_module_permission(self, request):
        return user_may_manage_organization(request.user)

    def has_view_permission(self, request, obj=None):
        return user_may_manage_organization(request.user)

    def has_change_permission(self, request, obj=None):
        return user_may_manage_organization(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.action(description="Ausgewählte Organisationsanfragen genehmigen")
def approve_registration_requests(modeladmin, request, queryset):
    User = get_user_model()

    approved_count = 0
    skipped_count = 0

    for registration_request in queryset:
        if registration_request.status != OrganizationRegistrationRequest.STATUS_PENDING:
            skipped_count += 1
            continue

        if Organization.objects.filter(slug=registration_request.organization_slug).exists():
            skipped_count += 1
            modeladmin.message_user(
                request,
                f"Organisation mit Slug '{registration_request.organization_slug}' existiert bereits.",
                level=messages.WARNING,
            )
            continue

        if User.objects.filter(email__iexact=registration_request.admin_email).exists():
            skipped_count += 1
            modeladmin.message_user(
                request,
                f"Benutzer mit E-Mail '{registration_request.admin_email}' existiert bereits. "
                "Bitte Organisation und Benutzerprofil manuell anlegen.",
                level=messages.WARNING,
            )
            continue

        username = registration_request.admin_email.lower()

        if User.objects.filter(username__iexact=username).exists():
            skipped_count += 1
            modeladmin.message_user(
                request,
                f"Benutzername '{username}' existiert bereits.",
                level=messages.WARNING,
            )
            continue

        organization = Organization.objects.create(
            name=registration_request.organization_name,
            slug=registration_request.organization_slug,
            is_active=True,
            is_public=True,
        )

        temporary_password = get_random_string(16)

        user = User.objects.create_user(
            username=username,
            email=registration_request.admin_email.lower(),
            password=temporary_password,
            first_name=registration_request.admin_first_name,
            last_name=registration_request.admin_last_name,
        )

        user.is_staff = True
        user.is_active = True
        user.save()

        UserProfile.objects.create(
            user=user,
            organization=organization,
            is_active_for_organization=True,
            is_org_admin=True,
            can_view_internal=True,
            can_inspect=True,
            can_maintain=True,
        )

        registration_request.status = OrganizationRegistrationRequest.STATUS_APPROVED
        registration_request.reviewed_at = timezone.now()
        registration_request.review_note = (
            registration_request.review_note
            or (
                f"Organisation '{organization.name}' und Organisations-Admin "
                f"'{user.username}' wurden automatisch angelegt."
            )
        )
        registration_request.save()

        approved_count += 1

        modeladmin.message_user(
            request,
            (
                f"Organisation '{organization.name}' wurde genehmigt. "
                f"Organisations-Admin: {user.email}. "
                f"Temporäres Passwort: {temporary_password}"
            ),
            level=messages.SUCCESS,
        )

    if approved_count:
        modeladmin.message_user(
            request,
            f"{approved_count} Organisationsanfrage(n) genehmigt.",
            level=messages.SUCCESS,
        )

    if skipped_count:
        modeladmin.message_user(
            request,
            f"{skipped_count} Organisationsanfrage(n) wurden übersprungen.",
            level=messages.WARNING,
        )


@admin.action(description="Ausgewählte Organisationsanfragen ablehnen")
def reject_registration_requests(modeladmin, request, queryset):
    updated = queryset.filter(
        status=OrganizationRegistrationRequest.STATUS_PENDING
    ).update(
        status=OrganizationRegistrationRequest.STATUS_REJECTED,
        reviewed_at=timezone.now(),
    )

    modeladmin.message_user(
        request,
        f"{updated} Organisationsanfrage(n) abgelehnt.",
        level=messages.WARNING,
    )


@admin.register(OrganizationRegistrationRequest)
class OrganizationRegistrationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "organization_slug",
        "admin_email",
        "status",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "organization_name",
        "organization_slug",
        "admin_email",
        "admin_first_name",
        "admin_last_name",
    )
    readonly_fields = ("created_at", "reviewed_at")
    actions = (
        approve_registration_requests,
        reject_registration_requests,
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
