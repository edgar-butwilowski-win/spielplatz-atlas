# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SpielplatzAtlasLoginView.as_view(), name="login"),
    path("profil/", views.profile_settings, name="profile_settings"),
    path("logout/", views.logout_view, name="logout"),
]
