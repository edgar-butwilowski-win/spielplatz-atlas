# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.utils import timezone

from inspections.models import Defect
from playgrounds.models import PlayEquipment, PlaygroundAccessory, PlaygroundSurface


TARGET_TYPE_NONE = "none"
TARGET_TYPE_EQUIPMENT = "equipment"
TARGET_TYPE_SURFACE = "surface"
TARGET_TYPE_ACCESSORY = "accessory"

TARGET_TYPE_CHOICES = [
    (TARGET_TYPE_NONE, "Allgemeiner Spielplatzmangel"),
    (TARGET_TYPE_EQUIPMENT, "Spielgerät"),
    (TARGET_TYPE_SURFACE, "Fallschutzfläche / Boden"),
    (TARGET_TYPE_ACCESSORY, "Zusatzausstattung"),
]


def apply_bootstrap_classes(form):
    for field in form.fields.values():
        existing_classes = field.widget.attrs.get("class", "")

        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "form-check-input"
        elif isinstance(field.widget, forms.RadioSelect):
            field.widget.attrs["class"] = "form-check-input"
        elif "form-control" not in existing_classes and "form-select" not in existing_classes:
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"


def restrict_target_fields_to_playground(form, playground):
    if not playground:
        return

    form.fields["equipment"].queryset = PlayEquipment.objects.filter(
        playground=playground,
        is_active=True,
    ).order_by("name")

    form.fields["surface"].queryset = PlaygroundSurface.objects.filter(
        playground=playground,
        is_active=True,
    ).order_by("name")

    form.fields["accessory"].queryset = PlaygroundAccessory.objects.filter(
        playground=playground,
        is_active=True,
    ).order_by("name")


def get_initial_target_type(instance):
    if not instance:
        return TARGET_TYPE_NONE

    if getattr(instance, "equipment_id", None):
        return TARGET_TYPE_EQUIPMENT

    if getattr(instance, "surface_id", None):
        return TARGET_TYPE_SURFACE

    if getattr(instance, "accessory_id", None):
        return TARGET_TYPE_ACCESSORY

    return TARGET_TYPE_NONE


def clean_single_target(cleaned_data):
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


def clean_target_by_type(cleaned_data):
    target_type = cleaned_data.get("target_type") or TARGET_TYPE_NONE

    equipment = cleaned_data.get("equipment")
    surface = cleaned_data.get("surface")
    accessory = cleaned_data.get("accessory")

    if target_type == TARGET_TYPE_NONE:
        cleaned_data["equipment"] = None
        cleaned_data["surface"] = None
        cleaned_data["accessory"] = None
        return cleaned_data

    if target_type == TARGET_TYPE_EQUIPMENT:
        cleaned_data["surface"] = None
        cleaned_data["accessory"] = None

        if not equipment:
            raise forms.ValidationError("Bitte das betroffene Spielgerät auswählen.")

        return cleaned_data

    if target_type == TARGET_TYPE_SURFACE:
        cleaned_data["equipment"] = None
        cleaned_data["accessory"] = None

        if not surface:
            raise forms.ValidationError("Bitte die betroffene Fallschutzfläche oder den betroffenen Boden auswählen.")

        return cleaned_data

    if target_type == TARGET_TYPE_ACCESSORY:
        cleaned_data["equipment"] = None
        cleaned_data["surface"] = None

        if not accessory:
            raise forms.ValidationError("Bitte die betroffene Zusatzausstattung auswählen.")

        return cleaned_data

    raise forms.ValidationError("Bitte eine gültige Objektart auswählen.")


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

        restrict_target_fields_to_playground(self, playground)
        apply_bootstrap_classes(self)

        self.fields["equipment"].required = False
        self.fields["surface"].required = False
        self.fields["accessory"].required = False
        self.fields["reported_by_text"].required = False
        self.fields["internal_note"].required = False
        self.fields["planned_resolution_date"].required = False
        self.fields["public_note"].required = False

    def clean(self):
        cleaned_data = super().clean()
        return clean_single_target(cleaned_data)


class DefectFromInspectionAnswerForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = (
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

    def __init__(self, *args, inspection_answer=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.inspection_answer = inspection_answer

        if not self.is_bound:
            self.initial.setdefault("reported_at", timezone.localtime().strftime("%Y-%m-%dT%H:%M"))
            self.initial.setdefault("source_type", Defect.SOURCE_INSPECTION)

            if inspection_answer and inspection_answer.comment:
                self.initial.setdefault("internal_description", inspection_answer.comment)

        apply_bootstrap_classes(self)

        self.fields["reported_by_text"].required = False
        self.fields["internal_note"].required = False
        self.fields["planned_resolution_date"].required = False
        self.fields["public_note"].required = False


class DefectEditForm(forms.ModelForm):
    target_type = forms.ChoiceField(
        label="Betroffenes Objekt",
        choices=TARGET_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        help_text="Wählen Sie zuerst die Objektart aus. Danach wird das passende Auswahlfeld aktiv.",
    )

    class Meta:
        model = Defect
        fields = (
            "target_type",
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
        widgets = DefectCreateForm.Meta.widgets

    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.playground = playground

        restrict_target_fields_to_playground(self, playground)
        apply_bootstrap_classes(self)

        if not self.is_bound:
            self.initial["target_type"] = get_initial_target_type(self.instance)

        self.fields["equipment"].required = False
        self.fields["surface"].required = False
        self.fields["accessory"].required = False
        self.fields["reported_by_text"].required = False
        self.fields["internal_note"].required = False
        self.fields["planned_resolution_date"].required = False
        self.fields["public_note"].required = False

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data = clean_target_by_type(cleaned_data)
        return clean_single_target(cleaned_data)
