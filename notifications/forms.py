# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django import forms
from django.contrib.auth import get_user_model


class DefectAssignmentForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label="Zuständige Person",
        queryset=get_user_model().objects.none(),
        required=False,
        empty_label="Keine Zuweisung",
        help_text="Die ausgewählte Person erhält eine Systemnachricht und, falls aktiviert, eine Push-Meldung.",
    )

    def __init__(self, *args, organization=None, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.current_user = current_user

        users = get_user_model().objects.filter(
            profile__organization=organization,
            profile__is_active_for_organization=True,
        ).filter(
            profile__is_org_admin=True
        ) | get_user_model().objects.filter(
            profile__organization=organization,
            profile__is_active_for_organization=True,
            profile__can_maintain=True,
        ) | get_user_model().objects.filter(
            profile__organization=organization,
            profile__is_active_for_organization=True,
            profile__can_inspect=True,
        )

        self.fields["assigned_to"].queryset = users.distinct().order_by(
            "last_name",
            "first_name",
            "username",
        )
        self.fields["assigned_to"].widget.attrs["class"] = "form-select"

    def clean_assigned_to(self):
        assigned_to = self.cleaned_data.get("assigned_to")

        if not assigned_to:
            return assigned_to

        if assigned_to.is_superuser:
            return assigned_to

        profile = getattr(assigned_to, "profile", None)

        if not profile:
            raise forms.ValidationError("Diese Person hat kein Benutzerprofil.")

        if profile.organization_id != self.organization.id:
            raise forms.ValidationError("Diese Person gehört nicht zur Organisation dieses Spielplatzes.")

        if not profile.is_active_for_organization:
            raise forms.ValidationError("Diese Person ist für die Organisation nicht aktiv.")

        if not profile.may_maintain:
            raise forms.ValidationError("Diese Person darf Mängel und Unterhalt nicht bearbeiten.")

        return assigned_to
