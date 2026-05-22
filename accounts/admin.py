# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError

from tenants.models import Organization

from .models import UserProfile
from .permissions import get_user_organization, user_may_manage_users


User = get_user_model()

ROLE_READER = "reader"
ROLE_INSPECTOR = "inspector"
ROLE_ORG_ADMIN = "org_admin"
ROLE_SUPERADMIN = "superadmin"

ROLE_CHOICES_FOR_SUPERUSER = (
    (ROLE_SUPERADMIN, "Superadmin"),
    (ROLE_ORG_ADMIN, "Organisations-Admin"),
    (ROLE_INSPECTOR, "Kontrolleur/in"),
    (ROLE_READER, "Lesender interner User"),
)

ROLE_CHOICES_FOR_ORG_ADMIN = (
    (ROLE_ORG_ADMIN, "Organisations-Admin"),
    (ROLE_INSPECTOR, "Kontrolleur/in"),
    (ROLE_READER, "Lesender interner User"),
)


def organization_for_user(user):
    return None if user.is_superuser else get_user_organization(user)


def profile_values_for_role(role):
    if role == ROLE_ORG_ADMIN:
        return {
            "is_org_admin": True,
            "can_view_internal": True,
            "can_inspect": True,
            "can_maintain": True,
        }

    if role == ROLE_INSPECTOR:
        return {
            "is_org_admin": False,
            "can_view_internal": True,
            "can_inspect": True,
            "can_maintain": True,
        }

    return {
        "is_org_admin": False,
        "can_view_internal": True,
        "can_inspect": False,
        "can_maintain": False,
    }


def user_should_have_django_admin_access(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_active_for_organization and profile.may_manage_organization)


def sync_django_admin_access(user):
    should_have_access = user_should_have_django_admin_access(user)

    if user.is_staff != should_have_access:
        user.is_staff = should_have_access
        user.save(update_fields=["is_staff"])


class SpielplatzAtlasUserCreationForm(forms.ModelForm):
    email = forms.EmailField(
        label="E-Mail-Adresse",
        help_text="Diese Adresse wird für die Anmeldung verwendet.",
    )
    first_name = forms.CharField(
        label="Vorname",
        required=False,
    )
    last_name = forms.CharField(
        label="Nachname",
        required=False,
    )
    organization = forms.ModelChoiceField(
        label="Organisation",
        queryset=Organization.objects.none(),
        required=False,
        help_text="Nur für interne Benutzer erforderlich. Superadmins sind mandantenübergreifend.",
    )
    role = forms.ChoiceField(
        label="Rolle",
        choices=ROLE_CHOICES_FOR_ORG_ADMIN,
        help_text="Die Rolle setzt die passenden internen Berechtigungen automatisch.",
    )
    password1 = forms.CharField(
        label="Passwort",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Das Passwort wird sofort für den neuen Benutzer gesetzt.",
    )
    password2 = forms.CharField(
        label="Passwort bestätigen",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
        )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

        if request and request.user.is_superuser:
            self.fields["role"].choices = ROLE_CHOICES_FOR_SUPERUSER
            self.fields["organization"].queryset = Organization.objects.all()
            return

        organization = organization_for_user(request.user) if request else None
        self.fields["role"].choices = ROLE_CHOICES_FOR_ORG_ADMIN

        if organization:
            self.fields["organization"].queryset = Organization.objects.filter(pk=organization.pk)
            self.fields["organization"].initial = organization
            self.fields["organization"].disabled = True
        else:
            self.fields["organization"].queryset = Organization.objects.none()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Es gibt bereits einen Benutzer mit dieser E-Mail-Adresse.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        organization = cleaned_data.get("organization")
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Die beiden Passwörter stimmen nicht überein.")

        if password1:
            password_validation.validate_password(password1, self.instance)

        if role == ROLE_SUPERADMIN:
            if not self.request or not self.request.user.is_superuser:
                self.add_error("role", "Nur Superadmins dürfen weitere Superadmins anlegen.")
        elif organization is None:
            self.add_error("organization", "Bitte eine Organisation auswählen.")

        if self.request and not self.request.user.is_superuser:
            own_organization = organization_for_user(self.request.user)

            if role == ROLE_SUPERADMIN:
                self.add_error("role", "Organisations-Admins dürfen keine Superadmins anlegen.")

            if organization != own_organization:
                self.add_error("organization", "Organisations-Admins dürfen nur Benutzer ihrer eigenen Organisation anlegen.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data["role"]
        email = self.cleaned_data["email"]
        organization = self.cleaned_data.get("organization")

        user.username = email
        user.email = email
        user.is_active = True
        user.is_superuser = role == ROLE_SUPERADMIN
        user.is_staff = role in (ROLE_SUPERADMIN, ROLE_ORG_ADMIN)
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

            if role != ROLE_SUPERADMIN:
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "organization": organization,
                        "is_active_for_organization": True,
                        **profile_values_for_role(role),
                    },
                )

            sync_django_admin_access(user)

        return user


class SpielplatzAtlasUserAdmin(DjangoUserAdmin):
    add_form = SpielplatzAtlasUserCreationForm
    add_fieldsets = (
        (
            "Benutzer hinzufügen",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "organization",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    list_display = (
        "email",
        "first_name",
        "last_name",
        "display_organization",
        "display_role",
        "is_active",
        "display_is_django_admin",
    )
    list_filter = (
        "is_active",
        "is_superuser",
        "profile__organization",
        "profile__is_org_admin",
        "profile__can_inspect",
        "profile__can_view_internal",
    )
    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
        "profile__organization__name",
    )
    ordering = ("email",)
    readonly_fields = (
        "display_is_django_admin",
        "last_login",
        "date_joined",
    )

    class Media:
        js = ("accounts/admin_user_password_generator.js",)

    @admin.display(description="Organisation")
    def display_organization(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.organization if profile else "Mandantenübergreifend"

    @admin.display(description="Rolle")
    def display_role(self, obj):
        if obj.is_superuser:
            return "Superadmin"

        profile = getattr(obj, "profile", None)

        if not profile:
            return "Keine interne Rolle"

        if profile.is_org_admin:
            return "Organisations-Admin"

        if profile.can_inspect:
            return "Kontrolleur/in"

        if profile.can_view_internal:
            return "Lesender interner User"

        return "Keine interne Rolle"

    @admin.display(boolean=True, description="Django-Admin-Zugang")
    def display_is_django_admin(self, obj):
        return obj.is_staff

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets

        if request.user.is_superuser:
            return (
                ("Login", {"fields": ("username", "email", "password")}),
                ("Name", {"fields": ("first_name", "last_name")}),
                ("Status", {"fields": ("is_active", "display_is_django_admin", "is_superuser")}),
                ("Zeitstempel", {"fields": ("last_login", "date_joined")}),
            )

        return (
            ("Login", {"fields": ("username", "email", "password")}),
            ("Name", {"fields": ("first_name", "last_name")}),
            ("Status", {"fields": ("is_active", "display_is_django_admin")}),
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))

        if not request.user.is_superuser:
            readonly.extend(["username", "email"])

        return tuple(dict.fromkeys(readonly))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if obj is not None:
            return form

        class RequestAwareUserCreationForm(form):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs["request"] = request
                super().__init__(*args, **inner_kwargs)

        return RequestAwareUserCreationForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(profile__organization=organization).distinct()

        return qs.none()

    def has_module_permission(self, request):
        return user_may_manage_users(request.user)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if not user_may_manage_users(request.user):
            return False

        if obj is None:
            return True

        profile = getattr(obj, "profile", None)
        return bool(profile and profile.organization == get_user_organization(request.user))

    def has_add_permission(self, request):
        return user_may_manage_users(request.user)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if not user_may_manage_users(request.user):
            return False

        if obj is None:
            return True

        profile = getattr(obj, "profile", None)
        return bool(profile and profile.organization == get_user_organization(request.user) and not obj.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_form(self, request, form, change):
        if not change:
            return form.save(commit=True)

        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        if change and not request.user.is_superuser and obj.is_superuser:
            raise PermissionDenied("Organisations-Admins dürfen keine Superadmins bearbeiten.")

        super().save_model(request, obj, form, change)
        sync_django_admin_access(obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "is_active_for_organization",
        "is_org_admin",
        "can_view_internal",
        "can_inspect",
        "can_maintain",
        "display_is_django_admin",
    )
    list_filter = (
        "organization",
        "is_active_for_organization",
        "is_org_admin",
        "can_view_internal",
        "can_inspect",
        "can_maintain",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "organization__name",
    )
    autocomplete_fields = (
        "user",
        "organization",
    )
    readonly_fields = ("display_is_django_admin",)

    @admin.display(boolean=True, description="Django-Admin-Zugang")
    def display_is_django_admin(self, obj):
        return obj.user.is_staff

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def has_module_permission(self, request):
        return user_may_manage_users(request.user)

    def has_view_permission(self, request, obj=None):
        return user_may_manage_users(request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if not user_may_manage_users(request.user):
            return False

        if obj is None:
            return True

        return obj.organization == get_user_organization(request.user) and not obj.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sync_django_admin_access(obj.user)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, SpielplatzAtlasUserAdmin)
