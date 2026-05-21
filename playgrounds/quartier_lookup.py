from .quartier_models import Quartier


def find_quartier_name_for_playground(playground):
    if not playground.longitude or not playground.latitude:
        return ""

    x = float(playground.longitude)
    y = float(playground.latitude)

    for quartier in Quartier.objects.filter(
        organization=playground.organization,
        is_active=True,
    ).only("name", "geom"):
        if geometry_contains_point(quartier.geom, x, y):
            return quartier.name

    return ""


def get_playground_quartier_name(playground):
    return playground.district or find_quartier_name_for_playground(playground)


def geometry_contains_point(geometry, x, y):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []

    if geometry_type == "Polygon":
        return polygon_contains_point(coordinates, x, y)

    if geometry_type == "MultiPolygon":
        return any(polygon_contains_point(polygon, x, y) for polygon in coordinates)

    return False


def polygon_contains_point(polygon, x, y):
    if not polygon:
        return False

    outer_ring = polygon[0]

    if not ring_contains_point(outer_ring, x, y):
        return False

    inner_rings = polygon[1:]
    return not any(ring_contains_point(ring, x, y) for ring in inner_rings)


def ring_contains_point(ring, x, y):
    inside = False
    point_count = len(ring)

    if point_count < 3:
        return False

    j = point_count - 1

    for i in range(point_count):
        xi, yi = ring[i][:2]
        xj, yj = ring[j][:2]

        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )

        if intersects:
            inside = not inside

        j = i

    return inside
