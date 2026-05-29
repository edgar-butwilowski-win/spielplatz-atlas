# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import hashlib

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from .forms import ProfileSettingsForm


LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_ATTEMPTS_PER_IP = 20
LOGIN_MAX_ATTEMPTS_PER_EMAIL = 8


def get_client_ip(request):
    return request.META.get("REMOTE_ADDR") or "unknown"


def stable_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def rate_limit_key(prefix, value):
    return f"spielplatzatlas:{prefix}:{stable_hash(value)}"


def get_rate_limit_count(key):
    return int(cache.get(key, 0) or 0)


def increment_rate_limit(key, timeout_seconds):
    if cache.add(key, 1, timeout_seconds):
        return 1

    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout_seconds)
        return 1


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

    def get_rate_limit_keys(self, form=None):
        ip_address = get_client_ip(self.request)
        keys = [
            rate_limit_key("login-ip", ip_address),
        ]

        username = ""

        if form is not None:
            username = (form.data.get(form.username_field) or "").strip().lower()
        elif self.request.method == "POST":
            username = (self.request.POST.get("username") or "").strip().lower()

        if username:
            keys.append(rate_limit_key("login-email", username))

        return keys

    def is_rate_limited(self, form=None):
        keys = self.get_rate_limit_keys(form)

        ip_count = get_rate_limit_count(keys[0])
        email_count = get_rate_limit_count(keys[1]) if len(keys) > 1 else 0

        return (
            ip_count >= LOGIN_MAX_ATTEMPTS_PER_IP
            or email_count >= LOGIN_MAX_ATTEMPTS_PER_EMAIL
        )

    def add_rate_limit_error(self, form):
        form.add_error(
            None,
            (
                "Es gab zu viele Anmeldeversuche. "
                "Bitte versuchen Sie es in einigen Minuten erneut."
            ),
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if self.is_rate_limited(form):
            self.add_rate_limit_error(form)
            return self.form_invalid(form)

        if form.is_valid():
            return self.form_valid(form)

        for key in self.get_rate_limit_keys(form):
            increment_rate_limit(key, LOGIN_RATE_LIMIT_WINDOW_SECONDS)

        return self.form_invalid(form)


@login_required
def profile_settings(request):
    if request.method == "POST":
        form = ProfileSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, _("Ihre Profileinstellungen wurden gespeichert."))
            return redirect("accounts:profile_settings")
    else:
        form = ProfileSettingsForm(instance=request.user)

    return render(request, "accounts/profile_settings.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("public:index")
