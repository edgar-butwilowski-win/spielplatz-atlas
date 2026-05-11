# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import re


class PublicAuthNavigationMiddleware:
    """Vereinheitlicht die Login-/Logout-/Admin-Navigation in öffentlichen Seiten.

    Die öffentlichen Templates sind aktuell noch nicht auf ein gemeinsames
    Basistemplate umgestellt. Diese Middleware verhindert deshalb, dass
    angemeldete interne Nicht-Admins über den Navigationsbutton in den
    Django-Admin gelangen, und zeigt den Admin-Button nur echten Admin-Usern.
    """

    ADMIN_LINK_PATTERN = re.compile(
        r'<a href="/admin/" class="btn btn-sm btn-outline-secondary">\s*(Admin|Login)\s*</a>'
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/admin/"):
            return response

        content_type = response.get("Content-Type", "")

        if "text/html" not in content_type or not hasattr(response, "content"):
            return response

        try:
            html = response.content.decode(response.charset or "utf-8")
        except UnicodeDecodeError:
            return response

        if request.user.is_authenticated:
            if self.user_should_see_admin_button(request.user):
                replacement = (
                    '<a href="/admin/" class="btn btn-sm btn-outline-secondary">Admin</a>'
                    '<a href="/logout/" class="btn btn-sm btn-outline-secondary">Logout</a>'
                )
            else:
                replacement = '<a href="/logout/" class="btn btn-sm btn-outline-secondary">Logout</a>'
        else:
            replacement = '<a href="/login/" class="btn btn-sm btn-outline-secondary">Login</a>'

        updated_html = self.ADMIN_LINK_PATTERN.sub(replacement, html)

        if updated_html == html:
            return response

        response.content = updated_html.encode(response.charset or "utf-8")
        response["Content-Length"] = str(len(response.content))
        return response

    @staticmethod
    def user_should_see_admin_button(user):
        if user.is_superuser:
            return True

        profile = getattr(user, "profile", None)

        return bool(
            profile
            and profile.may_manage_organization
        )
