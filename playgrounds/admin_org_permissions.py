from accounts.admin_utils import user_is_org_admin

from .admin import (
    EquipmentSupplierAdmin,
    EquipmentTypeAdmin,
    PlayEquipmentAdmin,
    PlaygroundAccessoryAdmin,
    PlaygroundAdmin,
    PlaygroundSurfaceAdmin,
)
from .quartier_admin import QuartierAdmin, QuartierImportAdmin


ORG_ADMIN_MODEL_ADMINS = (
    PlaygroundAdmin,
    EquipmentTypeAdmin,
    EquipmentSupplierAdmin,
    PlayEquipmentAdmin,
    PlaygroundSurfaceAdmin,
    PlaygroundAccessoryAdmin,
    QuartierAdmin,
    QuartierImportAdmin,
)


def has_org_admin_module_permission(self, request):
    return user_is_org_admin(request.user)


def has_org_admin_view_permission(self, request, obj=None):
    return user_is_org_admin(request.user)


def has_org_admin_add_permission(self, request):
    return user_is_org_admin(request.user)


def has_org_admin_change_permission(self, request, obj=None):
    return user_is_org_admin(request.user)


def install_org_admin_permissions():
    for admin_class in ORG_ADMIN_MODEL_ADMINS:
        admin_class.has_module_permission = has_org_admin_module_permission
        admin_class.has_view_permission = has_org_admin_view_permission
        admin_class.has_add_permission = has_org_admin_add_permission
        admin_class.has_change_permission = has_org_admin_change_permission


install_org_admin_permissions()
