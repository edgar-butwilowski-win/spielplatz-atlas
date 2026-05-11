# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse


def user_should_enter_admin(user):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return bool(
        profile
        and profile.may_manage_organization
    )


class SpielplatzAtlasLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        if user_should_enter_admin(self.request.user):
            return reverse("admin:index")

        return reverse("public:index")


def logout_view(request):
    logout(request)
    return redirect("public:index")
