from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import UserProfile
from accounts.permissions import get_user_organization, user_may_manage_organization
from accounts.utils import generate_internal_username, normalize_email
from inspections.planning import rebuild_planning_for_organization

from .models import Organization, OrganizationRegistrationRequest


@admin.action(description="Kontrollplanung neu berechnen")
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
        modeladmin.message_user(request, f"{organization.name}: erstellt {result['created']}, aktualisiert {result['updated']}, unveraendert {result['unchanged']}.", level=messages.SUCCESS)

    if processed_count:
        modeladmin.message_user(request, f"{processed_count} Organisation(en) verarbeitet. Gesamt erstellt: {total_created}, aktualisiert: {total_updated}, unveraendert: {total_unchanged}.", level=messages.SUCCESS)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    change_form_template = "admin/tenants/organization/change_form.html"
    list_display = ("name", "slug", "is_active", "is_public", "primary_color", "secondary_color", "created_at")
    list_filter = ("is_active", "is_public")
    search_fields = ("name", "slug")
    actions = (rebuild_inspection_planning_for_organizations,)

    def get_prepopulated_fields(self, request, obj=None):
        if request.user.is_superuser:
            return {"slug": ("name",)}
        return {}

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<path:object_id>/rebuild-inspection-planning/", self.admin_site.admin_view(self.rebuild_inspection_planning_view), name="tenants_organization_rebuild_planning"),
        ]
        return custom_urls + urls

    def rebuild_inspection_planning_view(self, request, object_id):
        organization = self.get_object(request, object_id)
        if not organization or not self.has_change_permission(request, organization):
            raise PermissionDenied
        if request.method != "POST":
            self.message_user(request, "Bitte den Button im Organisationsformular verwenden.", level=messages.WARNING)
            return redirect(reverse("admin:tenants_organization_change", args=[organization.pk]))
        result = rebuild_planning_for_organization(organization)
        self.message_user(request, f"Kontrollplanung neu berechnet. Erstellt: {result['created']}, aktualisiert: {result['updated']}, unveraendert: {result['unchanged']}.", level=messages.SUCCESS)
        return redirect(reverse("admin:tenants_organization_change", args=[organization.pk]))

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            organization = self.get_object(request, object_id)
            if organization and self.has_change_permission(request, organization):
                extra_context.update({
                    "show_rebuild_inspection_planning": True,
                    "rebuild_inspection_planning_url": reverse("admin:tenants_organization_rebuild_planning", args=[organization.pk]),
                })
        return super().changeform_view(request, object_id, form_url, extra_context)

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
            return ("name", "slug", "is_active", "is_public", "primary_color", "secondary_color", "logo")
        return ("name", "primary_color", "secondary_color", "logo")

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


@admin.action(description="Ausgewaehlte Organisationsanfragen genehmigen")
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
            modeladmin.message_user(request, f"Organisation mit Slug '{registration_request.organization_slug}' existiert bereits.", level=messages.WARNING)
            continue
        admin_email = normalize_email(registration_request.admin_email)
        if User.objects.filter(email__iexact=admin_email).exists():
            skipped_count += 1
            modeladmin.message_user(request, f"Benutzer mit E-Mail '{admin_email}' existiert bereits. Bitte Organisation und Benutzerprofil manuell anlegen.", level=messages.WARNING)
            continue

        organization = Organization.objects.create(name=registration_request.organization_name, slug=registration_request.organization_slug, is_active=True, is_public=True)
        temp_password = get_random_string(16)
        user = User.objects.create_user(username=generate_internal_username(), email=admin_email, password=temp_password, first_name=registration_request.admin_first_name, last_name=registration_request.admin_last_name)
        user.is_staff = True
        user.is_active = True
        user.save()
        UserProfile.objects.create(user=user, organization=organization, role=UserProfile.ROLE_ORG_ADMIN, is_active_for_organization=True)
        registration_request.status = OrganizationRegistrationRequest.STATUS_APPROVED
        registration_request.reviewed_at = timezone.now()
        registration_request.review_note = registration_request.review_note or f"Organisation '{organization.name}' und Organisations-Admin '{user.email}' wurden automatisch angelegt."
        registration_request.save()
        approved_count += 1
        modeladmin.message_user(request, f"Organisation '{organization.name}' wurde genehmigt. Organisations-Admin: {user.email}. Temporaeres Passwort: {temp_password}", level=messages.SUCCESS)

    if approved_count:
        modeladmin.message_user(request, f"{approved_count} Organisationsanfrage(n) genehmigt.", level=messages.SUCCESS)
    if skipped_count:
        modeladmin.message_user(request, f"{skipped_count} Organisationsanfrage(n) wurden uebersprungen.", level=messages.WARNING)


@admin.action(description="Ausgewaehlte Organisationsanfragen ablehnen")
def reject_registration_requests(modeladmin, request, queryset):
    updated = queryset.filter(status=OrganizationRegistrationRequest.STATUS_PENDING).update(status=OrganizationRegistrationRequest.STATUS_REJECTED, reviewed_at=timezone.now())
    modeladmin.message_user(request, f"{updated} Organisationsanfrage(n) abgelehnt.", level=messages.WARNING)


@admin.register(OrganizationRegistrationRequest)
class OrganizationRegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "organization_slug", "admin_email", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("organization_name", "organization_slug", "admin_email", "admin_first_name", "admin_last_name")
    readonly_fields = ("created_at", "reviewed_at")
    actions = (approve_registration_requests, reject_registration_requests)

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
