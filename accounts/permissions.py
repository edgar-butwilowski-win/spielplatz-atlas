from django.core.exceptions import PermissionDenied


PERMISSION_DENIED_ORGANIZATION = "Keine Berechtigung für diese Organisation."


def get_active_profile(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)

    if not profile or not profile.is_active_for_organization:
        return None

    return profile


def get_user_organization(user):
    profile = get_active_profile(user)
    return profile.organization if profile else None


def get_active_profile_for_organization(user, organization):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None

    profile = get_active_profile(user)

    if not profile:
        return None

    if profile.organization_id != organization.id:
        return None

    return profile


def user_may_view_internal(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)
    return bool(profile and profile.may_view_internal)


def user_may_inspect(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)
    return bool(profile and profile.may_inspect)


def user_may_maintain(user, organization):
    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, organization)
    return bool(profile and profile.may_maintain)


def user_may_manage_organization(user, organization=None):
    if user.is_superuser:
        return True

    if organization is None:
        profile = get_active_profile(user)
        return bool(profile and profile.may_manage_organization)

    profile = get_active_profile_for_organization(user, organization)
    return bool(profile and profile.may_manage_organization)


def user_may_manage_users(user, organization=None):
    return user_may_manage_organization(user, organization)


def require_internal_view_permission(user, organization):
    if user_may_view_internal(user, organization):
        return True

    raise PermissionDenied(PERMISSION_DENIED_ORGANIZATION)


def require_inspection_permission(user, organization):
    if user_may_inspect(user, organization):
        return True

    raise PermissionDenied("Keine Berechtigung zum Erfassen von Kontrollen.")


def require_maintenance_permission(user, organization):
    if user_may_maintain(user, organization):
        return True

    raise PermissionDenied("Keine Berechtigung für Mängel und Unterhalt.")


def require_defect_permission(user, organization):
    if user_may_maintain(user, organization) or user_may_inspect(user, organization):
        return True

    raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Mängeln.")


def require_org_admin_permission(user, organization):
    if user_may_manage_organization(user, organization):
        return True

    raise PermissionDenied("Keine Berechtigung zur Verwaltung dieser Organisation.")
