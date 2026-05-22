import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from django.db import transaction
from django.utils import timezone

from .quartier_lookup import find_quartier_name_for_playground
from .quartier_models import Quartier


NAME_ATTRIBUTE = "Quartiername"
GEOMETRY_ATTRIBUTE = "geom"
WFS_TIMEOUT_SECONDS = 30


class QuartierImportError(ValueError):
    pass


def import_quartiere_from_import_config(import_config):
    if import_config.geojson_file:
        import_config.geojson_file.open("rb")
        try:
            data = import_config.geojson_file.read().decode("utf-8-sig")
        finally:
            import_config.geojson_file.close()
        feature_collection = json.loads(data)
        source = import_config.geojson_file.name
    elif import_config.wfs_endpoint:
        feature_collection = fetch_wfs_feature_collection(import_config.wfs_endpoint)
        source = import_config.wfs_endpoint
    else:
        raise QuartierImportError("Bitte entweder eine GeoJSON-Datei hochladen oder einen WFS-Endpoint angeben.")

    return import_quartiere_from_feature_collection(
        organization=import_config.organization,
        feature_collection=feature_collection,
        source=source,
        replace_existing=import_config.replace_existing,
    )


def fetch_wfs_feature_collection(endpoint):
    capabilities_xml = fetch_url_text(endpoint)
    feature_type_name = get_first_feature_type_name(capabilities_xml)

    if not feature_type_name:
        raise QuartierImportError("Im WFS-Capabilities-Dokument wurde kein FeatureType gefunden.")

    feature_url = build_wfs_getfeature_url(endpoint, feature_type_name)
    feature_text = fetch_url_text(feature_url)

    try:
        return json.loads(feature_text)
    except json.JSONDecodeError as exc:
        raise QuartierImportError(
            "Der WFS hat kein gültiges GeoJSON geliefert. Bitte prüfen, ob outputFormat=application/json unterstützt wird."
        ) from exc


def fetch_url_text(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SpielplatzAtlas/1.0"},
    )

    with urllib.request.urlopen(request, timeout=WFS_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def get_first_feature_type_name(capabilities_xml):
    root = ET.fromstring(capabilities_xml)

    for element in root.iter():
        if element.tag.endswith("FeatureType"):
            for child in element:
                if child.tag.endswith("Name") and child.text:
                    return child.text.strip()

    return ""


def build_wfs_getfeature_url(endpoint, feature_type_name):
    parsed = urllib.parse.urlparse(endpoint)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    service = query.get("service") or query.get("Service") or "WFS"

    query.update({
        "service": service,
        "request": "GetFeature",
        "typeName": feature_type_name,
        "outputFormat": "application/json",
    })

    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def import_quartiere_from_feature_collection(organization, feature_collection, source="", replace_existing=False):
    if feature_collection.get("type") != "FeatureCollection":
        raise QuartierImportError("Die Quelldaten müssen eine GeoJSON FeatureCollection sein.")

    features = feature_collection.get("features") or []

    imported = 0
    skipped = 0
    errors = []

    with transaction.atomic():
        if replace_existing:
            Quartier.objects.filter(organization=organization).update(is_active=False)

        for index, feature in enumerate(features, start=1):
            try:
                name, geometry = extract_quartier_feature(feature)
            except QuartierImportError as exc:
                skipped += 1
                errors.append(f"Feature {index}: {exc}")
                continue

            Quartier.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    "geom": geometry,
                    "source": source,
                    "is_active": True,
                    "imported_at": timezone.now(),
                },
            )
            imported += 1

        playgrounds_updated = update_playground_districts_for_organization(organization)

    return {
        "imported": imported,
        "skipped": skipped,
        "playgrounds_updated": playgrounds_updated,
        "errors": errors,
    }


def update_playground_districts_for_organization(organization):
    from .models import Playground

    updated = 0
    playgrounds = Playground.objects.filter(
        organization=organization,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    for playground in playgrounds:
        quartier_name = find_quartier_name_for_playground(playground)

        if quartier_name and playground.district != quartier_name:
            playground.district = quartier_name
            playground.save(update_fields=["district"])
            updated += 1

    return updated


def extract_quartier_feature(feature):
    properties = feature.get("properties") or {}
    name = (properties.get(NAME_ATTRIBUTE) or feature.get(NAME_ATTRIBUTE) or "").strip()

    geometry = (
        properties.get(GEOMETRY_ATTRIBUTE)
        or feature.get(GEOMETRY_ATTRIBUTE)
        or feature.get("geometry")
    )

    if not name:
        raise QuartierImportError(f"Attribut {NAME_ATTRIBUTE!r} fehlt oder ist leer.")

    if not is_supported_geometry(geometry):
        raise QuartierImportError(f"Attribut {GEOMETRY_ATTRIBUTE!r} enthält keine Polygon- oder MultiPolygon-Geometrie.")

    return name, geometry


def is_supported_geometry(geometry):
    return (
        isinstance(geometry, dict)
        and geometry.get("type") in {"Polygon", "MultiPolygon"}
        and bool(geometry.get("coordinates"))
    )
