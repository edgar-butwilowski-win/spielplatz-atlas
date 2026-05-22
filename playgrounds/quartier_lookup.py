from django.contrib.gis.geos import Point

from .geo_constants import LV95_SRID
from .quartier_models import Quartier


def find_quartier_name_for_playground(playground):
    if playground.location:
        quartier = (
            Quartier.objects
            .filter(
                organization=playground.organization,
                is_active=True,
                geometry__isnull=False,
                geometry__contains=playground.location,
            )
            .only("name")
            .first()
        )

        if quartier:
            return quartier.name

    if not playground.longitude or not playground.latitude:
        return ""

    # Fallback für unvollständig migrierte Bestandsdaten.
    x = float(playground.longitude)
    y = float(playground.latitude)
    point = Point(x, y, srid=LV95_SRID)

    quartier = (
        Quartier.objects
        .filter(
            organization=playground.organization,
            is_active=True,
            geometry__isnull=False,
            geometry__contains=point,
        )
        .only("name")
        .first()
    )

    if quartier:
        return quartier.name

    return ""


def get_playground_quartier_name(playground):
    return playground.district or find_quartier_name_for_playground(playground)
