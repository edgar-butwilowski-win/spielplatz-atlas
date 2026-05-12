# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.core.management.base import BaseCommand, CommandError

from inspections.planning import rebuild_planning_for_organization
from tenants.models import Organization


class Command(BaseCommand):
    help = "Berechnet Kontrollregeln und Kontrollaufträge für aktive Spielplätze neu."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Optional: Nur diese Organisation neu berechnen.",
        )
        parser.add_argument(
            "--organization-slug",
            type=str,
            help="Optional: Nur diese Organisation anhand des URL-Kürzels neu berechnen.",
        )

    def handle(self, *args, **options):
        organization_id = options.get("organization_id")
        organization_slug = options.get("organization_slug")

        if organization_id and organization_slug:
            raise CommandError("Bitte entweder --organization-id oder --organization-slug verwenden, nicht beides.")

        organizations = Organization.objects.filter(is_active=True).order_by("name")

        if organization_id:
            organizations = organizations.filter(id=organization_id)

        if organization_slug:
            organizations = organizations.filter(slug=organization_slug)

        if not organizations.exists():
            raise CommandError("Keine passende aktive Organisation gefunden.")

        total = {
            "organizations": 0,
            "rules": 0,
            "playgrounds": 0,
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "status_refreshed": 0,
        }

        for organization in organizations:
            result = rebuild_planning_for_organization(organization)
            total["organizations"] += 1

            for key in ["rules", "playgrounds", "created", "updated", "unchanged", "status_refreshed"]:
                total[key] += result[key]

            self.stdout.write(
                self.style.SUCCESS(
                    f"{organization.name}: "
                    f"{result['created']} neu, "
                    f"{result['updated']} aktualisiert, "
                    f"{result['unchanged']} unverändert, "
                    f"{result['status_refreshed']} Status aktualisiert."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Fertig: "
                f"{total['organizations']} Organisation(en), "
                f"{total['rules']} Regel(n), "
                f"{total['playgrounds']} Spielplatz/Spielplätze, "
                f"{total['created']} neue Kontrollaufträge."
            )
        )
