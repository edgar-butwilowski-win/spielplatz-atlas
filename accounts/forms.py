# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


UserModel = get_user_model()


class ProfileSettingsForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Passwort"),
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Mindestens 8 Zeichen eingeben. Leer lassen, um das aktuelle Passwort beizubehalten."),
    )

    class Meta:
        model = UserModel
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": _("Vorname"),
            "last_name": _("Nachname"),
            "email": _("Mail-Adresse"),
        }
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            css_classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css_classes + " form-control").strip()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()

        if not email:
            raise ValidationError(_("Bitte geben Sie eine Mail-Adresse ein."))

        duplicate_exists = (
            UserModel.objects
            .filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if duplicate_exists:
            raise ValidationError(_("Diese Mail-Adresse wird bereits von einem anderen Benutzer verwendet."))

        return email

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""

        if not password:
            return password

        if len(password) < 8:
            raise ValidationError(_("Das Passwort muss mindestens 8 Zeichen enthalten."))

        password_validation.validate_password(password, self.instance)

        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user
