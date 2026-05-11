# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("api/playgrounds/", views.public_playgrounds_api, name="playgrounds_api"),
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
