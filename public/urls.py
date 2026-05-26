from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("impressum/", views.imprint, name="imprint"),
    path("api/playgrounds/", views.public_playgrounds_api, name="playgrounds_api"),
    path("api/playgrounds/<int:playground_id>/popup/", views.public_playground_popup_api, name="playground_popup_api"),
    path(
        "playground-documents/<int:document_id>/download/",
        views.playground_document_download,
        name="playground_document_download",
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
