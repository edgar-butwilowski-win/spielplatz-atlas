# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from .permissions import get_user_organization, user_may_manage_organization


def user_is_org_admin(user):
    return user_may_manage_organization(user)


class OrganizationAdminPermissionMixin:
    """Admin permission helper for organisation-scoped Django admin models."""

    def user_can_manage_organization(self, request):
        return user_may_manage_organization(request.user)

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
