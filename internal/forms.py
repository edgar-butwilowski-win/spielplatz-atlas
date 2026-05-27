from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from inspections.models import Defect
from playgrounds.models import PlayEquipment, PlaygroundAccessory, PlaygroundSurface

TARGET_TYPE_NONE = "none"
TARGET_TYPE_EQUIPMENT = "equipment"
TARGET_TYPE_SURFACE = "surface"
TARGET_TYPE_ACCESSORY = "accessory"

HTML_DATE_FORMAT = "%Y-%m-%d"
HTML_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"

TARGET_TYPE_CHOICES = [
    (TARGET_TYPE_NONE, _("General playground defect")),
    (TARGET_TYPE_EQUIPMENT, _("Play equipment")),
    (TARGET_TYPE_SURFACE, _("Impact protection surface / ground")),
    (TARGET_TYPE_ACCESSORY, _("Additional equipment")),
]


def apply_bootstrap_classes(form):
    for field in form.fields.values():
        existing_classes = field.widget.attrs.get("class", "")
        if isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs["class"] = "form-check-input"
        elif isinstance(field.widget, forms.RadioSelect):
            field.widget.attrs["class"] = "form-check-input"
        elif "form-control" not in existing_classes and "form-select" not in existing_classes:
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"


def use_html_date_input(field):
    field.input_formats = [HTML_DATE_FORMAT]
    field.widget.format = HTML_DATE_FORMAT


def use_html_datetime_input(field):
    field.input_formats = [HTML_DATETIME_FORMAT]
    field.widget.format = HTML_DATETIME_FORMAT


def restrict_target_fields_to_playground(form, playground):
    if not playground:
        return
    form.fields["equipment"].queryset = PlayEquipment.objects.filter(playground=playground, is_active=True).order_by("name")
    form.fields["surface"].queryset = PlaygroundSurface.objects.filter(playground=playground, is_active=True).order_by("name")
    form.fields["accessory"].queryset = PlaygroundAccessory.objects.filter(playground=playground, is_active=True).order_by("name")


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
    selected_targets = [value for value in [cleaned_data.get("equipment"), cleaned_data.get("surface"), cleaned_data.get("accessory")] if value is not None]
    if len(selected_targets) > 1:
        raise forms.ValidationError(_("Please select at most one affected object: play equipment, impact protection surface or additional equipment."))
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
            raise forms.ValidationError(_("Please select the affected play equipment."))
        return cleaned_data
    if target_type == TARGET_TYPE_SURFACE:
        cleaned_data["equipment"] = None
        cleaned_data["accessory"] = None
        if not surface:
            raise forms.ValidationError(_("Please select the affected impact protection surface or ground."))
        return cleaned_data
    if target_type == TARGET_TYPE_ACCESSORY:
        cleaned_data["equipment"] = None
        cleaned_data["surface"] = None
        if not accessory:
            raise forms.ValidationError(_("Please select the affected additional equipment."))
        return cleaned_data
    raise forms.ValidationError(_("Please select a valid object type."))


def clean_urgency_by_safety_risk(cleaned_data):
    if cleaned_data.get("has_safety_risk") and not cleaned_data.get("urgency"):
        cleaned_data["urgency"] = Defect.URGENCY_A
    if not cleaned_data.get("has_safety_risk"):
        cleaned_data["urgency"] = ""
    return cleaned_data


class EquipmentRenovationForm(forms.ModelForm):
    class Meta:
        model = PlayEquipment
        fields = ("recommended_renovation_year", "renovation_type", "renovation_comment")
        widgets = {
            "recommended_renovation_year": forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": _("e.g. 2028"), "min": 1000, "max": 9999}),
            "renovation_type": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "renovation_comment": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": _("Optional comment")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["recommended_renovation_year"].required = False
        self.fields["renovation_type"].required = False
        self.fields["renovation_comment"].required = False

    def clean_recommended_renovation_year(self):
        year = self.cleaned_data.get("recommended_renovation_year")
        if year is None:
            return year
        if year < 1000 or year > 9999:
            raise forms.ValidationError(_("Please enter a four-digit year."))
        return year


class DefectCreateForm(forms.ModelForm):
    target_type = forms.ChoiceField(label=_("Affected object"), choices=TARGET_TYPE_CHOICES, widget=forms.RadioSelect, required=True, help_text=_("First select the object type. The matching selection field will then become active."))

    class Meta:
        model = Defect
        fields = ("target_type", "equipment", "surface", "accessory", "source_type", "reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "planned_resolution_date", "public_visible", "public_note")
        widgets = {
            "reported_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}, format=HTML_DATETIME_FORMAT),
            "planned_resolution_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format=HTML_DATE_FORMAT),
            "internal_description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "internal_note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "public_note": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.playground = playground
        restrict_target_fields_to_playground(self, playground)
        apply_bootstrap_classes(self)
        use_html_datetime_input(self.fields["reported_at"])
        use_html_date_input(self.fields["planned_resolution_date"])
        if not self.is_bound:
            if self.initial.get("equipment"):
                self.initial["target_type"] = TARGET_TYPE_EQUIPMENT
            elif self.initial.get("surface"):
                self.initial["target_type"] = TARGET_TYPE_SURFACE
            elif self.initial.get("accessory"):
                self.initial["target_type"] = TARGET_TYPE_ACCESSORY
            else:
                self.initial["target_type"] = TARGET_TYPE_NONE
        for name in ["equipment", "surface", "accessory", "reported_by_text", "internal_note", "planned_resolution_date", "public_note"]:
            self.fields[name].required = False

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data = clean_target_by_type(cleaned_data)
        cleaned_data = clean_single_target(cleaned_data)
        return clean_urgency_by_safety_risk(cleaned_data)


class DefectFromInspectionAnswerForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = ("reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "planned_resolution_date", "public_visible", "public_note")
        widgets = DefectCreateForm.Meta.widgets

    def __init__(self, *args, inspection_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.inspection_answer = inspection_answer
        use_html_datetime_input(self.fields["reported_at"])
        use_html_date_input(self.fields["planned_resolution_date"])
        if not self.is_bound:
            self.initial.setdefault("reported_at", timezone.localtime().strftime(HTML_DATETIME_FORMAT))
            self.initial.setdefault("source_type", Defect.SOURCE_INSPECTION)
            if inspection_answer and inspection_answer.comment:
                self.initial.setdefault("internal_description", inspection_answer.comment)
        apply_bootstrap_classes(self)
        for name in ["reported_by_text", "internal_note", "planned_resolution_date", "public_note"]:
            self.fields[name].required = False

    def clean(self):
        return clean_urgency_by_safety_risk(super().clean())


class DefectEditForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = ("source_type", "reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "planned_resolution_date", "public_visible", "public_note")
        widgets = DefectCreateForm.Meta.widgets

    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.playground = playground
        use_html_datetime_input(self.fields["reported_at"])
        use_html_date_input(self.fields["planned_resolution_date"])
        apply_bootstrap_classes(self)
        for name in ["reported_by_text", "internal_note", "planned_resolution_date", "public_note"]:
            self.fields[name].required = False

    def clean(self):
        return clean_urgency_by_safety_risk(super().clean())
