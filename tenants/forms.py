# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.contrib.auth import get_user_model

from .models import Organization, OrganizationRegistrationRequest


class OrganizationRegistrationRequestForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "tabindex": "-1",
        }),
    )

    class Meta:
        model = OrganizationRegistrationRequest
        fields = [
            "organization_name",
            "organization_slug",
            "admin_first_name",
            "admin_last_name",
            "admin_email",
            "message",
        ]

        labels = {
            "organization_name": "Name der Organisation",
            "organization_slug": "Kurzname / URL-Kennung",
            "admin_first_name": "Vorname",
            "admin_last_name": "Nachname",
            "admin_email": "E-Mail-Adresse",
            "message": "Nachricht",
        }

        help_texts = {
            "organization_slug": "Zum Beispiel: stadt-winterthur oder gemeinde-beispiel.",
            "message": "Optional: kurzer Hinweis zur Organisation oder zum geplanten Einsatz.",
        }

        widgets = {
            "organization_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "z. B. Stadt Winterthur",
            }),
            "organization_slug": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "z. B. stadt-winterthur",
            }),
            "admin_first_name": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "admin_last_name": forms.TextInput(attrs={
                "class": "form-control",
            }),
            "admin_email": forms.EmailInput(attrs={
                "class": "form-control",
            }),
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
            }),
        }

    def clean_website(self):
        value = self.cleaned_data.get("website", "")

        if value:
            raise forms.ValidationError("Die Anfrage konnte nicht verarbeitet werden.")

        return value

    def clean_organization_name(self):
        name = self.cleaned_data["organization_name"].strip()

        if Organization.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                "Für diese Organisation besteht bereits ein Eintrag."
            )

        pending_request_exists = OrganizationRegistrationRequest.objects.filter(
            organization_name__iexact=name,
            status=OrganizationRegistrationRequest.STATUS_PENDING,
        ).exists()

        if pending_request_exists:
            raise forms.ValidationError(
                "Für diese Organisation liegt bereits eine offene Anfrage vor."
            )

        return name

    def clean_organization_slug(self):
        slug = self.cleaned_data["organization_slug"].strip().lower()

        if Organization.objects.filter(slug__iexact=slug).exists():
            raise forms.ValidationError(
                "Diese URL-Kennung wird bereits verwendet."
            )

        pending_request_exists = OrganizationRegistrationRequest.objects.filter(
            organization_slug__iexact=slug,
            status=OrganizationRegistrationRequest.STATUS_PENDING,
        ).exists()

        if pending_request_exists:
            raise forms.ValidationError(
                "Für diese URL-Kennung liegt bereits eine offene Anfrage vor."
            )

        return slug

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].strip().lower()
        User = get_user_model()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Für diese E-Mail-Adresse besteht bereits ein Benutzerkonto."
            )

        pending_request_exists = OrganizationRegistrationRequest.objects.filter(
            admin_email__iexact=email,
            status=OrganizationRegistrationRequest.STATUS_PENDING,
        ).exists()

        if pending_request_exists:
            raise forms.ValidationError(
                "Für diese E-Mail-Adresse liegt bereits eine offene Anfrage vor."
            )

        return email
