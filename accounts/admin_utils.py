# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.


def get_user_organization(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)

    if not profile or not profile.is_active_for_organization:
        return None

    return profile.organization


def user_is_org_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    return bool(profile and profile.may_manage_organization)


class OrganizationAdminPermissionMixin:
    """Admin permission helper for organisation-scoped Django admin models."""

    def user_can_manage_organization(self, request):
        return user_is_org_admin(request.user)

    def has_module_permission(self, request):
        return self.user_can_manage_organization(request)

    def has_view_permission(self, request, obj=None):
        return self.user_can_manage_organization(request)

    def has_add_permission(self, request):
        return self.user_can_manage_organization(request)

    def has_change_permission(self, request, obj=None):
        return self.user_can_manage_organization(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
