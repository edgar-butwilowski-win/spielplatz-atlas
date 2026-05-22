# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .permissions import user_may_manage_organization


ORG_ADMIN_MANAGED_MODELS = {
    "accounts.user",
    "accounts.userprofile",
    "tenants.organization",
    "playgrounds.playground",
    "playgrounds.equipmenttype",
    "playgrounds.equipmentsupplier",
    "playgrounds.playequipment",
    "playgrounds.playgroundsurface",
    "playgrounds.playgroundaccessory",
    "playgrounds.playgrounddocument",
    "playgrounds.quartier",
    "playgrounds.quartierimport",
    "inspections.inspectioncriterion",
    "inspections.inspectioncriterionapplicability",
    "inspections.inspection",
    "inspections.inspectionscope",
    "inspections.inspectionanswer",
    "inspections.defect",
    "inspections.defectimage",
    "inspections.maintenanceaction",
    "media_assets.imageasset",
    "notifications.systemnotification",
    "notifications.pushsubscription",
}

ORG_ADMIN_ALLOWED_ACTIONS = {"view", "add", "change"}


class EmailAuthenticationBackend(ModelBackend):
    """Authentifiziert interne Benutzer über ihre E-Mail-Adresse.

    Fachliche Admin-Rechte werden aus UserProfile/may_*-Properties abgeleitet.
    Django-Gruppen sind damit nicht mehr die Quelle der fachlichen Berechtigung.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or kwargs.get("email") or "").strip().lower()

        if not email or password is None:
            return None

        UserModel = get_user_model()

        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def has_perm(self, user_obj, perm, obj=None):
        if user_obj.is_active and user_obj.is_superuser:
            return True

        if super().has_perm(user_obj, perm, obj=obj):
            return True

        if not user_obj.is_active or not user_obj.is_staff:
            return False

        if not user_may_manage_organization(user_obj):
            return False

        try:
            app_label, codename = perm.split(".", 1)
            action, model_name = codename.split("_", 1)
        except ValueError:
            return False

        if action == "delete":
            return False

        if action not in ORG_ADMIN_ALLOWED_ACTIONS:
            return False

        return f"{app_label}.{model_name}" in ORG_ADMIN_MANAGED_MODELS
