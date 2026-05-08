# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms

from inspections.models import Defect
from playgrounds.models import PlayEquipment, PlaygroundAccessory, PlaygroundSurface


class DefectCreateForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = (
            "equipment",
            "surface",
            "accessory",
            "source_type",
            "reported_at",
            "reported_by_text",
            "internal_description",
            "internal_note",
            "has_safety_risk",
            "status",
            "planned_resolution_date",
            "public_visible",
            "public_note",
        )
        widgets = {
            "reported_at": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "planned_resolution_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "internal_description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                }
            ),
            "internal_note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                }
            ),
            "public_note": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                }
            ),
        }

    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.playground = playground

        if playground:
            self.fields["equipment"].queryset = PlayEquipment.objects.filter(
                playground=playground,
                is_active=True,
            ).order_by("name")

            self.fields["surface"].queryset = PlaygroundSurface.objects.filter(
                playground=playground,
                is_active=True,
            ).order_by("name")

            self.fields["accessory"].queryset = PlaygroundAccessory.objects.filter(
                playground=playground,
                is_active=True,
            ).order_by("name")

        for field in self.fields.values():
            existing_classes = field.widget.attrs.get("class", "")

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif "form-control" not in existing_classes and "form-select" not in existing_classes:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs["class"] = "form-select"
                else:
                    field.widget.attrs["class"] = "form-control"

        self.fields["equipment"].required = False
        self.fields["surface"].required = False
        self.fields["accessory"].required = False
        self.fields["reported_by_text"].required = False
        self.fields["internal_note"].required = False
        self.fields["planned_resolution_date"].required = False
        self.fields["public_note"].required = False

    def clean(self):
        cleaned_data = super().clean()

        equipment = cleaned_data.get("equipment")
        surface = cleaned_data.get("surface")
        accessory = cleaned_data.get("accessory")

        selected_targets = [
            value for value in [equipment, surface, accessory] if value is not None
        ]

        if len(selected_targets) > 1:
            raise forms.ValidationError(
                "Bitte höchstens ein betroffenes Objekt auswählen: Spielgerät, Fallschutzfläche oder Zusatzausstattung."
            )

        return cleaned_data