from django.urls import path

from . import map_views, photo_views, views

app_name = "public"

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("impressum/", views.imprint, name="imprint"),
    path("api/playgrounds/", map_views.public_playgrounds_api, name="playgrounds_api"),
    path("api/playgrounds/<int:playground_id>/popup/", map_views.public_playground_popup_api, name="playground_popup_api"),
    path(
        "playground-documents/<int:document_id>/download/",
        views.playground_document_download,
        name="playground_document_download",
    ),
    path(
        "playgrounds/<slug:organization_slug>/",
        map_views.organization_index,
        name="organization_index",
    ),
    path(
        "playgrounds/<slug:organization_slug>/<slug:playground_slug>/photo/upload/",
        photo_views.upload_playground_photo,
        name="upload_playground_photo",
    ),
    path(
        "playgrounds/<slug:organization_slug>/<slug:playground_slug>/photo/rotate/",
        photo_views.rotate_playground_photo,
        name="rotate_playground_photo",
    ),
    path(
        "equipment/<int:equipment_id>/photo/upload/",
        photo_views.upload_equipment_photo,
        name="upload_equipment_photo",
    ),
    path(
        "equipment/<int:equipment_id>/photo/rotate/",
        photo_views.rotate_equipment_photo,
        name="rotate_equipment_photo",
    ),
    path(
        "playgrounds/<slug:organization_slug>/<slug:playground_slug>/",
        views.playground_detail,
        name="playground_detail",
    ),
    path(
        "register-organization/",
        views.register_organization,
        name="register_organization",
    ),
    path(
        "register-organization/done/",
        views.register_organization_done,
        name="register_organization_done",
    ),
]
