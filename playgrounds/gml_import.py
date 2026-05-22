import xml.etree.ElementTree as ET

from .quartier_import import NAME_ATTRIBUTE, GEOMETRY_ATTRIBUTE, QuartierImportError


def parse_gml_feature_collection(gml_text):
    try:
        root = ET.fromstring(gml_text)
    except ET.ParseError as exc:
        raise QuartierImportError("Der WFS hat weder gültiges GeoJSON noch gültiges Simple-GML/XML geliefert.") from exc

    features = []

    for feature_element in iter_candidate_feature_elements(root):
        name_element = find_direct_child_by_local_name(feature_element, NAME_ATTRIBUTE)
        geom_element = find_direct_child_by_local_name(feature_element, GEOMETRY_ATTRIBUTE)

        if name_element is None or geom_element is None:
            continue

        name = text_content(name_element).strip()
        geometry = parse_gml_geometry(geom_element)

        if name and geometry:
            features.append({
                "type": "Feature",
                "properties": {
                    NAME_ATTRIBUTE: name,
                    GEOMETRY_ATTRIBUTE: geometry,
                },
                "geometry": geometry,
            })

    if not features:
        raise QuartierImportError(
            "Im Simple-GML des WFS wurden keine Features mit Quartiername und geom gefunden."
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def iter_candidate_feature_elements(root):
    for element in root.iter():
        if (
            find_direct_child_by_local_name(element, NAME_ATTRIBUTE) is not None
            and find_direct_child_by_local_name(element, GEOMETRY_ATTRIBUTE) is not None
        ):
            yield element


def get_local_name(tag):
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def text_content(element):
    return "".join(element.itertext()) if element is not None else ""


def find_direct_child_by_local_name(element, local_name):
    for child in list(element):
        if get_local_name(child.tag) == local_name:
            return child
    return None


def find_first_descendant_by_local_names(element, local_names):
    local_name_set = set(local_names)
    for descendant in element.iter():
        if get_local_name(descendant.tag) in local_name_set:
            return descendant
    return None


def find_descendants_by_local_names(element, local_names):
    local_name_set = set(local_names)
    return [
        descendant for descendant in element.iter()
        if get_local_name(descendant.tag) in local_name_set
    ]


def parse_gml_geometry(geom_element):
    geometry_element = find_first_descendant_by_local_names(
        geom_element,
        ("MultiSurface", "MultiPolygon", "Polygon", "Surface"),
    )

    if geometry_element is None:
        return None

    geometry_type = get_local_name(geometry_element.tag)

    if geometry_type in {"Polygon", "Surface"}:
        polygon = parse_gml_polygon(geometry_element)
        if polygon:
            return {"type": "Polygon", "coordinates": polygon}
        return None

    polygons = []
    for polygon_element in find_descendants_by_local_names(geometry_element, ("Polygon", "Surface")):
        if polygon_element is geometry_element:
            continue
        polygon = parse_gml_polygon(polygon_element)
        if polygon:
            polygons.append(polygon)

    if polygons:
        return {"type": "MultiPolygon", "coordinates": polygons}

    return None


def parse_gml_polygon(polygon_element):
    exterior_ring = None
    interior_rings = []

    for boundary_name in ("exterior", "outerBoundaryIs"):
        boundary = find_first_descendant_by_local_names(polygon_element, (boundary_name,))
        if boundary is not None:
            exterior_ring = parse_first_linear_ring(boundary)
            if exterior_ring:
                break

    for boundary in find_descendants_by_local_names(polygon_element, ("interior", "innerBoundaryIs")):
        ring = parse_first_linear_ring(boundary)
        if ring:
            interior_rings.append(ring)

    if not exterior_ring:
        rings = [
            parse_gml_linear_ring(ring_element)
            for ring_element in find_descendants_by_local_names(polygon_element, ("LinearRing",))
        ]
        rings = [ring for ring in rings if ring]
        if not rings:
            return None
        exterior_ring = rings[0]
        interior_rings = rings[1:]

    return [exterior_ring, *interior_rings]


def parse_first_linear_ring(element):
    ring_element = find_first_descendant_by_local_names(element, ("LinearRing", "Ring"))
    if ring_element is None:
        return None
    return parse_gml_linear_ring(ring_element)


def parse_gml_linear_ring(ring_element):
    pos_list = find_first_descendant_by_local_names(ring_element, ("posList",))
    if pos_list is not None:
        return parse_gml_pos_list(pos_list)

    coordinates = find_first_descendant_by_local_names(ring_element, ("coordinates",))
    if coordinates is not None:
        return parse_gml_coordinates(coordinates)

    pos_elements = find_descendants_by_local_names(ring_element, ("pos",))
    if pos_elements:
        return [
            parse_coordinate_pair(text_content(pos))
            for pos in pos_elements
            if text_content(pos).strip()
        ]

    return None


def parse_gml_pos_list(pos_list_element):
    values = [float(value) for value in text_content(pos_list_element).replace(",", " ").split()]
    dimension = get_srs_dimension(pos_list_element) or 2

    if len(values) % dimension != 0 and len(values) % 2 == 0:
        dimension = 2
    elif len(values) % dimension != 0 and len(values) % 3 == 0:
        dimension = 3

    coordinates = []
    for index in range(0, len(values), dimension):
        coordinate = values[index:index + dimension]
        if len(coordinate) >= 2:
            coordinates.append([coordinate[0], coordinate[1]])

    return coordinates


def get_srs_dimension(element):
    value = element.attrib.get("srsDimension") or element.attrib.get("dimension")
    if value:
        try:
            return int(value)
        except ValueError:
            return None
    return None


def parse_gml_coordinates(coordinates_element):
    text = text_content(coordinates_element).strip()
    tuple_separator = coordinates_element.attrib.get("ts", " ")
    coordinate_separator = coordinates_element.attrib.get("cs", ",")

    tuples = text.split() if tuple_separator == " " else [part for part in text.split(tuple_separator) if part.strip()]

    coordinates = []
    for tuple_text in tuples:
        parts = tuple_text.split(coordinate_separator) if coordinate_separator in tuple_text else tuple_text.replace(",", " ").split()
        if len(parts) >= 2:
            coordinates.append([float(parts[0]), float(parts[1])])

    return coordinates


def parse_coordinate_pair(text):
    values = [float(value) for value in text.replace(",", " ").split()]
    return [values[0], values[1]]
