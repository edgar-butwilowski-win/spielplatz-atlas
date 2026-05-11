# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import re


class PublicAuthNavigationMiddleware:
    """Vereinheitlicht die öffentliche Navigation.

    Die öffentlichen Templates sind aktuell noch nicht auf ein gemeinsames
    Basistemplate umgestellt. Diese Middleware reduziert die sichtbare
    Navigationsleiste auf die wichtigsten öffentlichen Links und ergänzt ein
    Burger-Menü für weitere Ziele wie Karte, Dashboard, Admin, Login und Logout.
    """

    NAV_ACTIONS_PATTERN = re.compile(
        r'(<nav class="navbar[\s\S]*?</a>\s*)'
        r'<div class="d-flex align-items-center gap-2">[\s\S]*?</div>'
        r'(\s*</div>\s*</nav>)',
        re.MULTILINE,
    )

    BODY_END_PATTERN = re.compile(r"</body>", re.IGNORECASE)

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

        updated_html = self.NAV_ACTIONS_PATTERN.sub(
            lambda match: f"{match.group(1)}{self.build_navigation_actions(request)}{match.group(2)}",
            html,
            count=1,
        )

        if updated_html != html and "atlas-menu-panel" in updated_html:
            updated_html = self.inject_menu_script(updated_html)

        if updated_html == html:
            return response

        response.content = updated_html.encode(response.charset or "utf-8")
        response["Content-Length"] = str(len(response.content))
        return response

    def build_navigation_actions(self, request):
        menu_links = [
            ("/", "Karte"),
        ]

        if request.user.is_authenticated:
            menu_links.append(("/internal/dashboard/", "Dashboard"))

            if self.user_should_see_admin_button(request.user):
                menu_links.append(("/admin/", "Admin"))

            menu_links.append(("/logout/", "Logout"))
        else:
            menu_links.append(("/login/", "Login"))

        menu_items = "".join(
            f'<a class="dropdown-item" href="{href}">{label}</a>'
            for href, label in menu_links
        )

        return f'''
            <div class="d-flex align-items-center gap-2 position-relative">
                <a href="/about/" class="btn btn-sm btn-outline-secondary d-none d-md-inline-flex">Über</a>
                <a href="/impressum/" class="btn btn-sm btn-outline-secondary d-none d-md-inline-flex">Impressum</a>
                <a href="/register-organization/" class="btn btn-sm btn-atlas-primary d-none d-md-inline-flex">Organisation registrieren</a>
                <button
                    type="button"
                    class="btn btn-sm btn-outline-secondary atlas-menu-toggle"
                    aria-label="Menü öffnen"
                    aria-expanded="false"
                >
                    ☰
                </button>
                <div class="atlas-menu-panel dropdown-menu dropdown-menu-end shadow">
                    <a class="dropdown-item d-md-none" href="/about/">Über</a>
                    <a class="dropdown-item d-md-none" href="/impressum/">Impressum</a>
                    <a class="dropdown-item d-md-none" href="/register-organization/">Organisation registrieren</a>
                    <div class="dropdown-divider d-md-none"></div>
                    {menu_items}
                </div>
            </div>
        '''

    def inject_menu_script(self, html):
        script = """
<script>
(function () {
    function closeAllMenus(exceptPanel) {
        document.querySelectorAll('.atlas-menu-panel.show').forEach(function (panel) {
            if (panel !== exceptPanel) {
                panel.classList.remove('show');
            }
        });
        document.querySelectorAll('.atlas-menu-toggle[aria-expanded="true"]').forEach(function (button) {
            if (!exceptPanel || button.nextElementSibling !== exceptPanel) {
                button.setAttribute('aria-expanded', 'false');
            }
        });
    }

    document.addEventListener('click', function (event) {
        var button = event.target.closest('.atlas-menu-toggle');

        if (button) {
            var panel = button.nextElementSibling;
            var isOpen = panel.classList.contains('show');
            closeAllMenus(panel);
            panel.classList.toggle('show', !isOpen);
            button.setAttribute('aria-expanded', String(!isOpen));
            event.preventDefault();
            return;
        }

        if (!event.target.closest('.atlas-menu-panel')) {
            closeAllMenus(null);
        }
    });
}());
</script>
"""

        return self.BODY_END_PATTERN.sub(script + "\n</body>", html, count=1)

    @staticmethod
    def user_should_see_admin_button(user):
        if user.is_superuser:
            return True

        profile = getattr(user, "profile", None)

        return bool(
            profile
            and profile.may_manage_organization
        )
