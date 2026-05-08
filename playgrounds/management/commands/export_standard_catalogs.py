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

from inspections.models import InspectionCriterion
from playgrounds.models import EquipmentType


STANDARD_VERSION = "SN-EN-1176-1177-v1"
CATALOG_DIR = Path(settings.BASE_DIR) / "data" / "standard_catalogs" / "sn_en_1176_1177_v1"


class Command(BaseCommand):
    help = "Exportiert den globalen Anbieter-Standardkatalog nach data/standard_catalogs."

    def handle(self, *args, **options):
        CATALOG_DIR.mkdir(parents=True, exist_ok=True)

        equipment_types_path = CATALOG_DIR / "equipment_types.json"
        inspection_criteria_path = CATALOG_DIR / "inspection_criteria.json"

        equipment_types_count = self.export_equipment_types(equipment_types_path)
        inspection_criteria_count = self.export_inspection_criteria(inspection_criteria_path)

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Standardkatalog exportiert: "
                    f"{equipment_types_count} Spielgerätearten, "
                    f"{inspection_criteria_count} Prüfkriterien."
                )
            )
        )

    def export_equipment_types(self, output_path):
        equipment_types = (
            EquipmentType.objects
            .filter(
                organization__isnull=True,
                is_standard=True,
            )
            .order_by("name", "code")
        )

        data = []

        for equipment_type in equipment_types:
            data.append(
                {
                    "name": equipment_type.name,
                    "code": equipment_type.code,
                    "norm_reference": equipment_type.norm_reference,
                    "standard_version": equipment_type.standard_version or STANDARD_VERSION,
                    "source_note": equipment_type.source_note,
                    "is_active": equipment_type.is_active,
                }
            )

        self.write_json(output_path, data)

        return len(data)

    def export_inspection_criteria(self, output_path):
        criteria = (
            InspectionCriterion.objects
            .filter(
                organization__isnull=True,
                is_standard=True,
            )
            .prefetch_related(
                "applicabilities",
                "applicabilities__equipment_types",
            )
            .order_by("area", "title")
        )

        data = []

        for criterion in criteria:
            applicabilities = []

            for applicability in criterion.applicabilities.all().order_by("scope_type"):
                equipment_type_codes = list(
                    applicability.equipment_types
                    .filter(
                        organization__isnull=True,
                        is_standard=True,
                    )
                    .order_by("code")
                    .values_list("code", flat=True)
                )

                applicabilities.append(
                    {
                        "scope_type": applicability.scope_type,
                        "applies_to_all_equipment": applicability.applies_to_all_equipment,
                        "equipment_type_codes": equipment_type_codes,
                    }
                )

            data.append(
                {
                    "area": criterion.area,
                    "title": criterion.title,
                    "inspection_text": criterion.inspection_text,
                    "maintenance_text": criterion.maintenance_text,
                    "norm_reference": criterion.norm_reference,
                    "minimum_inspection_type": criterion.minimum_inspection_type,
                    "standard_version": criterion.standard_version or STANDARD_VERSION,
                    "source_note": criterion.source_note,
                    "is_active": criterion.is_active,
                    "applicabilities": applicabilities,
                }
            )

        self.write_json(output_path, data)

        return len(data)

    def write_json(self, output_path, data):
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")