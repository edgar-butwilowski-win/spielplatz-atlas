from django.contrib import admin

from accounts.permissions import get_user_organization, user_may_manage_organization

from .models import ImageAsset


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "organization",
        "mime_type",
        "size_bytes",
        "public_visible",
        "created_at",
    )
    list_filter = ("organization", "mime_type", "public_visible")
    search_fields = ("original_filename", "sha256")
    readonly_fields = ("sha256", "size_bytes", "width", "height", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request.user)
        if organization:
            return qs.filter(organization=organization)
        return qs.none()

    def has_module_permission(self, request):
        return user_may_manage_organization(request.user)

    def has_view_permission(self, request, obj=None):
        if not user_may_manage_organization(request.user):
            return False
        if request.user.is_superuser or obj is None:
            return True
        organization = get_user_organization(request.user)
        return bool(organization and obj.organization_id == organization.id)

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_add_permission(self, request):
        return user_may_manage_organization(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
