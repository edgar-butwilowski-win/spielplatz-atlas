from .permissions import (
    get_user_organization,
    user_may_manage_organization,
)


class OrganizationAdminAccessMixin:
    """Allow only superusers and organisation admins to access a ModelAdmin."""

    def has_module_permission(self, request):
        return user_may_manage_organization(request.user)

    def has_view_permission(self, request, obj=None):
        return user_may_manage_organization(request.user)

    def has_add_permission(self, request):
        return user_may_manage_organization(request.user)

    def has_change_permission(self, request, obj=None):
        return user_may_manage_organization(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class OrganizationScopedQuerysetMixin:
    """Scope a ModelAdmin queryset to the active user's organisation."""

    organization_field = "organization"

    def get_user_organization(self, request):
        return get_user_organization(request.user)

    def scope_queryset_to_organization(self, qs, request):
        if request.user.is_superuser:
            return qs

        organization = self.get_user_organization(request)

        if not organization:
            return qs.none()

        return qs.filter(**{self.organization_field: organization})

    def get_queryset(self, request):
        return self.scope_queryset_to_organization(super().get_queryset(request), request)


class OrganizationScopedAdminMixin(OrganizationAdminAccessMixin, OrganizationScopedQuerysetMixin):
    """Base mixin for organisation-owned admin models."""

    pass


class SuperuserOnlyDeleteMixin:
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
