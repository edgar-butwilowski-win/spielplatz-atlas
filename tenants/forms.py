# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms

from .models import OrganizationRegistrationRequest


class OrganizationRegistrationRequestForm(forms.ModelForm):
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

    def clean_organization_slug(self):
        slug = self.cleaned_data["organization_slug"].strip().lower()
        return slug