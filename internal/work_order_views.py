from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from inspections.work_orders import WorkOrder
from tenants.models import Organization

from .permissions import get_active_profile_for_organization, require_org_admin_permission

HTML_DATE_FORMAT = "%Y-%m-%d"
RENOVATION_ACTIVE_STATUSES = [WorkOrder.STATUS_OPEN, WorkOrder.STATUS_PLANNED, WorkOrder.STATUS_IN_PROGRESS, WorkOrder.STATUS_SUSPENDED]


class WorkOrderUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        full_name = user.get_full_name().strip()
        if full_name and user.email:
            return "%s (%s)" % (full_name, user.email)
        return full_name or user.email or "Benutzer ohne E-Mail"


class RenovationWorkOrderForm(forms.ModelForm):
    assigned_to = WorkOrderUserChoiceField(queryset=get_user_model().objects.none(), required=False, widget=forms.Select(attrs={"class": "form-select form-select-sm"}))

    class Meta:
        model = WorkOrder
        fields = ("status", "planned_date", "assigned_to", "estimated_costs", "credit_name", "internal_note")
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "planned_date": forms.DateInput(format=HTML_DATE_FORMAT, attrs={"type": "date", "class": "form-control form-control-sm"}),
            "estimated_costs": forms.NumberInput(attrs={"class": "form-control form-control-sm", "min": "0", "step": "0.05", "placeholder": "CHF"}),
            "credit_name": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "internal_note": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["planned_date"].required = False
        self.fields["planned_date"].input_formats = [HTML_DATE_FORMAT]
        self.fields["planned_date"].widget.format = HTML_DATE_FORMAT
        self.fields["assigned_to"].queryset = self.get_assignable_users()
        for name in ["estimated_costs", "credit_name", "internal_note"]:
            self.fields[name].required = False

    def get_assignable_users(self):
        if not self.organization:
            return get_user_model().objects.none()
        return get_user_model().objects.filter(is_active=True).filter(Q(is_superuser=True) | (Q(profile__organization=self.organization) & Q(profile__is_active_for_organization=True) & Q(profile__role=UserProfile.ROLE_ORG_ADMIN))).distinct().order_by("last_name", "first_name", "email")

    def clean_estimated_costs(self):
        value = self.cleaned_data.get("estimated_costs")
        if value is not None and value < Decimal("0"):
            raise forms.ValidationError("Die Kostenschaetzung darf nicht negativ sein.")
        return value


def get_order_scope(user):
    if user.is_superuser:
        return {"organization": None, "is_superadmin": True, "can_manage": True}
    profile = getattr(user, "profile", None)
    if not profile:
        return None
    profile = get_active_profile_for_organization(user, profile.organization)
    if not profile or not profile.may_manage_organization:
        return None
    return {"organization": profile.organization, "is_superadmin": False, "can_manage": True}


def get_selected_organization(request, scope):
    if not scope["is_superadmin"]:
        return scope["organization"]
    organization_id = request.GET.get("organization") or request.POST.get("organization")
    if organization_id:
        return get_object_or_404(Organization, id=organization_id, is_active=True)
    return None


def work_order_redirect_url(organization_id=None):
    url = reverse("internal:work_orders")
    return "%s?organization=%s" % (url, organization_id) if organization_id else url


def build_credit_summary(queryset):
    rows = queryset.values("renovation_year", "credit_name").annotate(total_costs=Sum("estimated_costs"), order_count=Count("id")).order_by("renovation_year", "credit_name")
    return [{"year": row["renovation_year"] or "ohne Jahr", "credit_name": row["credit_name"] or "Noch keinem Sammelkredit zugewiesen", "total_costs": row["total_costs"], "count": row["order_count"]} for row in rows]


def add_order_forms(work_orders):
    order_list = list(work_orders[:200])
    for order in order_list:
        order.management_form = RenovationWorkOrderForm(instance=order, organization=order.organization)
    return order_list


@login_required
def work_orders(request):
    scope = get_order_scope(request.user)
    if not scope:
        raise PermissionDenied("Keine Berechtigung fuer die Auftragsverwaltung.")
    selected_organization = get_selected_organization(request, scope)
    if selected_organization:
        require_org_admin_permission(request.user, selected_organization)
    organizations = Organization.objects.filter(is_active=True).order_by("name") if scope["is_superadmin"] else []
    orders = WorkOrder.objects.select_related("organization", "playground", "equipment", "equipment__equipment_type", "assigned_to").filter(order_type=WorkOrder.TYPE_RENOVATION)
    if selected_organization:
        orders = orders.filter(organization=selected_organization)
    elif not scope["is_superadmin"]:
        orders = orders.none()
    status_filter = request.GET.get("status") or "active"
    year_filter = request.GET.get("year") or ""
    credit_filter = request.GET.get("credit") or ""
    if status_filter == "active":
        filtered_orders = orders.filter(status__in=RENOVATION_ACTIVE_STATUSES)
    elif status_filter:
        filtered_orders = orders.filter(status=status_filter)
    else:
        filtered_orders = orders
    if year_filter:
        filtered_orders = filtered_orders.filter(renovation_year=year_filter)
    if credit_filter:
        filtered_orders = filtered_orders.filter(credit_name=credit_filter)
    years = orders.exclude(renovation_year__isnull=True).values_list("renovation_year", flat=True).distinct().order_by("renovation_year")
    credits = orders.exclude(credit_name="").values_list("credit_name", flat=True).distinct().order_by("credit_name")
    return render(request, "internal/work_orders.html", {**scope, "selected_organization": selected_organization, "organizations": organizations, "orders": add_order_forms(filtered_orders.order_by("renovation_year", "playground__name", "equipment__name")), "status_filter": status_filter, "year_filter": year_filter, "credit_filter": credit_filter, "status_choices": [("active", "Aktive Auftraege")] + list(WorkOrder.STATUS_CHOICES), "years": years, "credits": credits, "credit_summary": build_credit_summary(orders.filter(order_type=WorkOrder.TYPE_RENOVATION))})


@login_required
@require_POST
def update_work_order(request, order_id):
    order = get_object_or_404(WorkOrder.objects.select_related("organization"), id=order_id)
    require_org_admin_permission(request.user, order.organization)
    form = RenovationWorkOrderForm(request.POST, instance=order, organization=order.organization)
    if form.is_valid():
        order = form.save(commit=False)
        try:
            order.full_clean()
            order.save()
            messages.success(request, "Der Auftrag wurde gespeichert.")
        except ValidationError as error:
            messages.error(request, error.messages[0] if error.messages else str(error))
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect(work_order_redirect_url(order.organization_id))
