# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

"""Admin permission hooks for organisation-scoped inspection models.

Django's admin index only shows registered models when the current user has
module and object permissions according to the model admin. SpielplatzAtlas uses
capabilities on UserProfile for organisation administration, so organisation
admins should see inspections and defects even if no separate Django auth model
permissions have been assigned.
"""

from django.contrib import admin

from accounts.permissions import get_user_organization, user_may_manage_organization
from inspections.models import Defect, Inspection


def _user_is_org_admin(user):
    return bool(user and user.is_authenticated and user_may_manage_organization(user))


def _object_belongs_to_user_organization(user, obj):
    if user.is_superuser:
        return True

    organization = get_user_organization(user)
    if not organization or not obj:
        return bool(organization)

    playground = getattr(obj, "playground", None)
    if not playground:
        return False

    return playground.organization_id == organization.id


def _has_module_permission(model_admin, request):
    return request.user.is_superuser or _user_is_org_admin(request.user)


def _has_view_permission(model_admin, request, obj=None):
    if request.user.is_superuser:
        return True

    if not _user_is_org_admin(request.user):
        return False

    if obj is None:
        return True

    return _object_belongs_to_user_organization(request.user, obj)


def _has_add_permission(model_admin, request):
    return request.user.is_superuser or _user_is_org_admin(request.user)


def _has_change_permission(model_admin, request, obj=None):
    if request.user.is_superuser:
        return True

    if not _user_is_org_admin(request.user):
        return False

    if obj is None:
        return True

    return _object_belongs_to_user_organization(request.user, obj)


def apply_admin_permissions():
    """Patch registered ModelAdmin instances for organisation admins."""

    for model in (Inspection, Defect):
        model_admin = admin.site._registry.get(model)
        if not model_admin:
            continue

        model_admin.has_module_permission = _has_module_permission.__get__(
            model_admin,
            model_admin.__class__,
        )
        model_admin.has_view_permission = _has_view_permission.__get__(
            model_admin,
            model_admin.__class__,
        )
        model_admin.has_add_permission = _has_add_permission.__get__(
            model_admin,
            model_admin.__class__,
        )
        model_admin.has_change_permission = _has_change_permission.__get__(
            model_admin,
            model_admin.__class__,
        )


apply_admin_permissions()
