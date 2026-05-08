# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from inspections.models import InspectionCriterion
from playgrounds.models import EquipmentType


DEFAULT_VERSION_DIR = "sn_en_1176_1177_v1"


class Command(BaseCommand):
    help = "Importiert den globalen Standardkatalog aus versionierten JSON-Dateien."

    def add_arguments(self, parser):
        parser.add_argument(
            "--version-dir",
            default=DEFAULT_VERSION_DIR,
            help="Verzeichnis unter data/standard_catalogs/, z. B. sn_en_1176_1177_v1.",
        )

    def handle(self, *args, **options):
        version_dir = options["version_dir"]

        base_dir = (
            Path(settings.BASE_DIR)
            / "data"
            / "standard_catalogs"
            / version_dir
        )

        equipment_path = base_dir / "equipment_types.json"
        criteria_path = base_dir / "inspection_criteria.json"

        if not equipment_path.exists():
            self.stderr.write(self.style.ERROR(f"Datei nicht gefunden: {equipment_path}"))
            return

        if not criteria_path.exists():
            self.stderr.write(self.style.ERROR(f"Datei nicht gefunden: {criteria_path}"))
            return

        equipment_data = self.read_json(equipment_path)
        criteria_data = self.read_json(criteria_path)

        with transaction.atomic():
            equipment_count = self.import_equipment_types(equipment_data)
            criteria_count = self.import_inspection_criteria(criteria_data)

        self.stdout.write(
            self.style.SUCCESS(
                f"Standardkatalog aus JSON importiert: "
                f"{equipment_count} Spielgerätearten, "
                f"{criteria_count} Prüfkriterien."
            )
        )

    def import_equipment_types(self, records):
        count = 0

        for record in records:
            code = record.get("code")
            name = record.get("name")

            if not code or not name:
                continue

            EquipmentType.objects.update_or_create(
                organization=None,
                code=code,
                defaults={
                    "name": name,
                    "norm_reference": record.get("norm_reference", ""),
                    "is_standard": True,
                    "standard_version": record.get("standard_version", ""),
                    "source_note": record.get("source_note", ""),
                    "is_locked": True,
                    "is_active": bool(record.get("is_active", True)),
                },
            )

            count += 1

        return count

    def import_inspection_criteria(self, records):
        count = 0

        for record in records:
            area = record.get("area", "")
            title = record.get("title", "")

            if not title:
                continue

            InspectionCriterion.objects.update_or_create(
                organization=None,
                area=area,
                title=title,
                defaults={
                    "inspection_text": record.get("inspection_text", ""),
                    "maintenance_text": record.get("maintenance_text", ""),
                    "norm_reference": record.get("norm_reference", ""),
                    "is_standard": True,
                    "standard_version": record.get("standard_version", ""),
                    "source_note": record.get("source_note", ""),
                    "is_locked": True,
                    "is_active": bool(record.get("is_active", True)),
                },
            )

            count += 1

        return count

    def read_json(self, path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)