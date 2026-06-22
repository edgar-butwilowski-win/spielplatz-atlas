from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from inspections.models import Defect
from inspections.work_orders import WorkOrder
from playgrounds.models import PlayEquipment, PlaygroundAccessory, PlaygroundSurface

TARGET_TYPE_NONE = "none"
TARGET_TYPE_EQUIPMENT = "equipment"
TARGET_TYPE_SURFACE = "surface"
TARGET_TYPE_ACCESSORY = "accessory"
HTML_DATE_FORMAT = "%Y-%m-%d"
HTML_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"
TARGET_TYPE_CHOICES = [(TARGET_TYPE_NONE, _("General playground defect")), (TARGET_TYPE_EQUIPMENT, _("Play equipment")), (TARGET_TYPE_SURFACE, _("Impact protection surface / ground")), (TARGET_TYPE_ACCESSORY, _("Additional equipment"))]
CREATE_STATUS_CHOICES = [(Defect.STATUS_OPEN, _("Open"))]
MANUAL_STATUS_CHOICES = [(Defect.STATUS_OPEN, _("Open")), (Defect.STATUS_DONE, _("Resolved")), (Defect.STATUS_VERIFIED, _("Checked / completed")), (Defect.STATUS_CANCELED, _("Canceled"))]


def apply_bootstrap_classes(form):
    for field in form.fields.values():
        if isinstance(field.widget, forms.CheckboxInput) or isinstance(field.widget, forms.RadioSelect):
            field.widget.attrs["class"] = "form-check-input"
        elif "class" not in field.widget.attrs:
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"


def use_html_datetime_input(field):
    field.input_formats = [HTML_DATETIME_FORMAT]
    field.widget.format = HTML_DATETIME_FORMAT


def restrict_target_fields_to_playground(form, playground):
    if playground:
        form.fields["equipment"].queryset = PlayEquipment.objects.filter(playground=playground, is_active=True).order_by("name")
        form.fields["surface"].queryset = PlaygroundSurface.objects.filter(playground=playground, is_active=True).order_by("name")
        form.fields["accessory"].queryset = PlaygroundAccessory.objects.filter(playground=playground, is_active=True).order_by("name")


def clean_target_by_type(cleaned_data):
    target_type = cleaned_data.get("target_type") or TARGET_TYPE_NONE
    if target_type == TARGET_TYPE_NONE:
        cleaned_data["equipment"] = None
        cleaned_data["surface"] = None
        cleaned_data["accessory"] = None
    elif target_type == TARGET_TYPE_EQUIPMENT:
        cleaned_data["surface"] = None
        cleaned_data["accessory"] = None
        if not cleaned_data.get("equipment"):
            raise forms.ValidationError(_("Please select the affected play equipment."))
    elif target_type == TARGET_TYPE_SURFACE:
        cleaned_data["equipment"] = None
        cleaned_data["accessory"] = None
        if not cleaned_data.get("surface"):
            raise forms.ValidationError(_("Please select the affected impact protection surface or ground."))
    elif target_type == TARGET_TYPE_ACCESSORY:
        cleaned_data["equipment"] = None
        cleaned_data["surface"] = None
        if not cleaned_data.get("accessory"):
            raise forms.ValidationError(_("Please select the affected additional equipment."))
    return cleaned_data


def clean_single_target(cleaned_data):
    targets = [cleaned_data.get("equipment"), cleaned_data.get("surface"), cleaned_data.get("accessory")]
    if len([target for target in targets if target is not None]) > 1:
        raise forms.ValidationError(_("Please select at most one affected object: play equipment, impact protection surface or additional equipment."))
    return cleaned_data


def clean_urgency_by_safety_risk(cleaned_data):
    if cleaned_data.get("has_safety_risk") and not cleaned_data.get("urgency"):
        cleaned_data["urgency"] = Defect.URGENCY_A
    if not cleaned_data.get("has_safety_risk"):
        cleaned_data["urgency"] = ""
    return cleaned_data


class EquipmentRenovationForm(forms.Form):
    renovation_year = forms.IntegerField(required=False, min_value=1000, max_value=9999, widget=forms.NumberInput(attrs={"class": "form-control form-control-sm"}))
    renovation_type = forms.ChoiceField(required=False, choices=[("", "---------")] + list(WorkOrder._meta.get_field("renovation_type").choices), widget=forms.Select(attrs={"class": "form-select form-select-sm"}))
    description = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control form-control-sm"}))

    def __init__(self, *args, instance=None, equipment=None, **kwargs):
        self.equipment = equipment or instance
        self.work_order = None
        if self.equipment:
            self.work_order = self.equipment.get_active_renovation_work_order()
        initial = kwargs.pop("initial", {})
        if self.work_order:
            initial = {**initial, "renovation_year": self.work_order.renovation_year, "renovation_type": self.work_order.renovation_type, "description": self.work_order.description}
        super().__init__(*args, initial=initial, **kwargs)

    def save(self):
        if not self.equipment:
            return None
        year = self.cleaned_data.get("renovation_year")
        renovation_type = self.cleaned_data.get("renovation_type") or ""
        description = self.cleaned_data.get("description") or ""
        order = self.work_order or WorkOrder(equipment=self.equipment, status=WorkOrder.STATUS_OPEN, priority=WorkOrder.PRIORITY_NORMAL)
        order.organization = self.equipment.playground.organization
        order.playground = self.equipment.playground
        order.title = "Sanierung %s" % self.equipment.name
        order.description = description
        order.order_type = WorkOrder.TYPE_RENOVATION
        order.source = WorkOrder.SOURCE_EQUIPMENT_RENOVATION
        order.renovation_type = renovation_type
        order.renovation_year = year
        order.due_date = timezone.datetime(year, 12, 31).date() if year else None
        if year and not order.credit_name:
            order.credit_name = "Sammelkredit Sanierungen %s" % year
        order.save()
        return order


class DefectCreateForm(forms.ModelForm):
    target_type = forms.ChoiceField(label=_("Affected object"), choices=TARGET_TYPE_CHOICES, widget=forms.RadioSelect, required=True)
    class Meta:
        model = Defect
        fields = ("target_type", "equipment", "surface", "accessory", "source_type", "reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "public_visible", "public_note")
        widgets = {"reported_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=HTML_DATETIME_FORMAT), "internal_description": forms.Textarea(attrs={"rows": 4}), "internal_note": forms.Textarea(attrs={"rows": 3}), "public_note": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)
        restrict_target_fields_to_playground(self, playground)
        apply_bootstrap_classes(self)
        use_html_datetime_input(self.fields["reported_at"])
        self.fields["status"].choices = CREATE_STATUS_CHOICES
        self.fields["status"].initial = Defect.STATUS_OPEN
        self.fields["status"].disabled = True
        if not self.is_bound:
            self.initial["target_type"] = TARGET_TYPE_EQUIPMENT if self.initial.get("equipment") else TARGET_TYPE_SURFACE if self.initial.get("surface") else TARGET_TYPE_ACCESSORY if self.initial.get("accessory") else TARGET_TYPE_NONE
        for name in ["equipment", "surface", "accessory", "reported_by_text", "internal_note", "public_note"]:
            self.fields[name].required = False
    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["status"] = Defect.STATUS_OPEN
        return clean_urgency_by_safety_risk(clean_single_target(clean_target_by_type(cleaned_data)))


class DefectFromInspectionAnswerForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = ("reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "public_visible", "public_note")
        widgets = DefectCreateForm.Meta.widgets
    def __init__(self, *args, inspection_answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        use_html_datetime_input(self.fields["reported_at"])
        self.fields["status"].choices = CREATE_STATUS_CHOICES
        self.fields["status"].initial = Defect.STATUS_OPEN
        self.fields["status"].disabled = True
        apply_bootstrap_classes(self)
        for name in ["reported_by_text", "internal_note", "public_note"]:
            self.fields[name].required = False
        if not self.is_bound and inspection_answer and inspection_answer.comment:
            self.initial.setdefault("internal_description", inspection_answer.comment)
    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["status"] = Defect.STATUS_OPEN
        return clean_urgency_by_safety_risk(cleaned_data)


class DefectEditForm(forms.ModelForm):
    class Meta:
        model = Defect
        fields = ("source_type", "reported_at", "reported_by_text", "internal_description", "internal_note", "has_safety_risk", "urgency", "status", "public_visible", "public_note")
        widgets = DefectCreateForm.Meta.widgets
    def __init__(self, *args, playground=None, **kwargs):
        super().__init__(*args, **kwargs)
        use_html_datetime_input(self.fields["reported_at"])
        self.fields["status"].choices = MANUAL_STATUS_CHOICES
        apply_bootstrap_classes(self)
        for name in ["reported_by_text", "internal_note", "public_note"]:
            self.fields[name].required = False
    def clean(self):
        return clean_urgency_by_safety_risk(super().clean())
