from django.core.exceptions import PermissionDenied


def get_active_profile_for_organization(user, organization):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)

    if not profile:
        return None

    if not profile.is_active_for_organization:
        return None

    if profile.organization_id != organization.id:
        return None

    return profile


def require_internal_view_permission(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)

    if profile and profile.may_view_internal:
        return True

    raise PermissionDenied("Keine Berechtigung für diese Organisation.")


def require_inspection_permission(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)

    if profile and profile.may_inspect:
        return True

    raise PermissionDenied("Keine Berechtigung zum Erfassen von Kontrollen.")


def require_maintenance_permission(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)

    if profile and profile.may_maintain:
        return True

    raise PermissionDenied("Keine Berechtigung für Mängel und Unterhalt.")


def require_defect_permission(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)

    if profile and (profile.may_maintain or profile.may_inspect):
        return True

    raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Mängeln.")


def require_org_admin_permission(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)

    if profile and profile.may_manage_organization:
        return True

    raise PermissionDenied("Keine Berechtigung zur Verwaltung dieser Organisation.")
