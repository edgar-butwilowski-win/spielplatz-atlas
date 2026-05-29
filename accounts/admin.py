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
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError

from tenants.models import Organization

from .models import UserProfile
from .permissions import get_user_organization, user_may_manage_users
from .utils import display_user, generate_internal_username, normalize_email


User = get_user_model()

ROLE_SUPERADMIN = "superadmin"

ROLE_CHOICES_FOR_SUPERUSER = (
    (ROLE_SUPERADMIN, "Superadmin"),
    (UserProfile.ROLE_ORG_ADMIN, "Organisations-Admin"),
    (UserProfile.ROLE_INSPECTOR, "Kontrolleur/in"),
    (UserProfile.ROLE_READER, "Lesender interner User"),
)

ROLE_CHOICES_FOR_ORG_ADMIN = (
    (UserProfile.ROLE_ORG_ADMIN, "Organisations-Admin"),
    (UserProfile.ROLE_INSPECTOR, "Kontrolleur/in"),
    (UserProfile.ROLE_READER, "Lesender interner User"),
)


class InternalUserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return display_user(obj)


def organization_for_user(user):
    return None if user.is_superuser else get_user_organization(user)


def user_role(user):
    if user.is_superuser:
        return ROLE_SUPERADMIN

    profile = getattr(user, "profile", None)

    if not profile:
        return UserProfile.ROLE_READER

    return profile.role


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


def sync_user_role(user, role, organization):
    if role == ROLE_SUPERADMIN:
        user.is_superuser = True
        user.is_staff = True
        UserProfile.objects.filter(user=user).delete()
        return

    user.is_superuser = False
    user.is_staff = role == UserProfile.ROLE_ORG_ADMIN
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "organization": organization,
            "role": role,
            "is_active_for_organization": True,
        },
    )


class SpielplatzAtlasUserCreationForm(forms.ModelForm):
    email = forms.EmailField(
        label="E-Mail-Adresse",
        help_text="Diese Adresse wird für die Anmeldung verwendet.",
    )
    first_name = forms.CharField(label="Vorname", required=False)
    last_name = forms.CharField(label="Nachname", required=False)
    organization = forms.ModelChoiceField(
        label="Organisation",
        queryset=Organization.objects.none(),
        required=False,
        help_text="Nur für interne Benutzer erforderlich. Superadmins sind mandantenübergreifend.",
    )
    role = forms.ChoiceField(
        label="Rolle",
        choices=ROLE_CHOICES_FOR_ORG_ADMIN,
        help_text="Die Rolle ist die Quelle der fachlichen Berechtigungen.",
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
        fields = ("email", "first_name", "last_name")

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
        email = normalize_email(self.cleaned_data["email"])

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
        organization = self.cleaned_data.get("organization")

        user.username = generate_internal_username()
        user.email = self.cleaned_data["email"]
        user.is_active = True
        user.set_password(self.cleaned_data["password1"])
        sync_user_role(user, role, organization)

        if commit:
            user.save()

            if role != ROLE_SUPERADMIN:
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "organization": organization,
                        "role": role,
                        "is_active_for_organization": True,
                    },
                )

            sync_django_admin_access(user)

        return user


class SpielplatzAtlasUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="Passwort")
    email = forms.EmailField(label="E-Mail-Adresse")
    first_name = forms.CharField(label="Vorname", required=False)
    last_name = forms.CharField(label="Nachname", required=False)
    organization = forms.ModelChoiceField(
        label="Organisation",
        queryset=Organization.objects.none(),
        required=False,
        help_text="Nur für interne Benutzer erforderlich. Superadmins sind mandantenübergreifend.",
    )
    role = forms.ChoiceField(
        label="Rolle",
        choices=ROLE_CHOICES_FOR_ORG_ADMIN,
        help_text="Die Rolle ist die Quelle der fachlichen Berechtigungen.",
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "password",
            "is_active",
        )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, "profile", None)

        if request and request.user.is_superuser:
            self.fields["role"].choices = ROLE_CHOICES_FOR_SUPERUSER
            self.fields["organization"].queryset = Organization.objects.all()
        else:
            organization = organization_for_user(request.user) if request else None
            self.fields["role"].choices = ROLE_CHOICES_FOR_ORG_ADMIN
            self.fields["organization"].queryset = Organization.objects.filter(pk=organization.pk) if organization else Organization.objects.none()
            self.fields["organization"].disabled = True

        self.fields["role"].initial = user_role(self.instance)

        if profile:
            self.fields["organization"].initial = profile.organization
        elif not self.instance.is_superuser:
            self.fields["organization"].initial = organization_for_user(request.user) if request else None

    def clean_email(self):
        email = normalize_email(self.cleaned_data["email"])
        qs = User.objects.filter(email__iexact=email)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Es gibt bereits einen Benutzer mit dieser E-Mail-Adresse.")

        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        organization = cleaned_data.get("organization")

        if role == ROLE_SUPERADMIN:
            if not self.request or not self.request.user.is_superuser:
                self.add_error("role", "Nur Superadmins dürfen Benutzer zu Superadmins machen.")
        elif organization is None:
            self.add_error("organization", "Bitte eine Organisation auswählen.")

        if self.request and not self.request.user.is_superuser:
            own_organization = organization_for_user(self.request.user)

            if role == ROLE_SUPERADMIN:
                self.add_error("role", "Organisations-Admins dürfen keine Superadmins verwalten.")

            if organization != own_organization:
                self.add_error("organization", "Organisations-Admins dürfen nur Benutzer ihrer eigenen Organisation verwalten.")

        return cleaned_data


class SpielplatzAtlasUserAdmin(DjangoUserAdmin):
    form = SpielplatzAtlasUserChangeForm
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
        "profile__role",
    )
    search_fields = (
        "email",
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

    @admin.display(description="Benutzer")
    def display_user(self, obj):
        return display_user(obj)

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

        return profile.get_role_display()

    @admin.display(boolean=True, description="Django-Admin-Zugang")
    def display_is_django_admin(self, obj):
        return obj.is_staff

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets

        return (
            ("Login", {"fields": ("email", "password")}),
            ("Name", {"fields": ("first_name", "last_name")}),
            ("Rolle und Organisation", {"fields": ("organization", "role")}),
            ("Status", {"fields": ("is_active", "display_is_django_admin")}),
            ("Zeitstempel", {"fields": ("last_login", "date_joined")}),
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        class RequestAwareForm(form):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs["request"] = request
                super().__init__(*args, **inner_kwargs)

        return RequestAwareForm

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("profile", "profile__organization")

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

        if not obj.username:
            obj.username = generate_internal_username()

        obj.email = normalize_email(obj.email)
        role = form.cleaned_data.get("role")
        organization = form.cleaned_data.get("organization")
        sync_user_role(obj, role, organization)
        super().save_model(request, obj, form, change)

        if role != ROLE_SUPERADMIN:
            UserProfile.objects.update_or_create(
                user=obj,
                defaults={
                    "organization": organization,
                    "role": role,
                    "is_active_for_organization": True,
                },
            )

        sync_django_admin_access(obj)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(UserProfile)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, SpielplatzAtlasUserAdmin)
