# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import json
import uuid
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.utils.text import slugify

from .models import Playground


class PlaygroundSyncError(Exception):
    pass


def is_null_string(value):
    return value is None or str(value).strip() == ""


def is_null_number(value):
    return value is None or value == -1


def value_or_none(value):
    if is_null_string(value):
        return None

    return str(value).strip()


def number_or_none(value):
    if is_null_number(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def decimal_or_none(value):
    if value is None or value == "":
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def build_address(street_name, house_number):
    street = value_or_none(street_name)
    house_no = value_or_none(house_number)

    if street and house_no:
        return f"{street} {house_no}"

    if street:
        return street

    return None


def create_unique_slug(name, organization, existing_playground=None):
    base_slug = slugify(name)[:80] or "spielplatz"
    slug = base_slug
    counter = 2

    queryset = Playground.objects.filter(
        organization=organization,
        slug=slug,
    )

    if existing_playground:
        queryset = queryset.exclude(id=existing_playground.id)

    while queryset.exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[:100 - len(suffix)]}{suffix}"
        queryset = Playground.objects.filter(
            organization=organization,
            slug=slug,
        )

        if existing_playground:
            queryset = queryset.exclude(id=existing_playground.id)

        counter += 1

    return slug


def fetch_feature_collection(url):
    request = Request(
        url,
        headers={
            "Accept": "application/json, application/geo+json",
            "User-Agent": "SpielplatzAtlas/1.0",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        raise PlaygroundSyncError(f"Der Webservice hat HTTP {error.code} zurückgegeben.") from error
    except URLError as error:
        raise PlaygroundSyncError(f"Der Webservice konnte nicht erreicht werden: {error.reason}") from error
    except TimeoutError as error:
        raise PlaygroundSyncError("Der Webservice hat nicht rechtzeitig geantwortet.") from error

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as error:
        raise PlaygroundSyncError("Die Antwort des Webservice ist kein gültiges JSON.") from error

    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        features = data.get("features") or []
    elif isinstance(data, list):
        features = data
    elif isinstance(data, dict) and data.get("type") == "Feature":
        features = [data]
    else:
        raise PlaygroundSyncError("Die Antwort des Webservice enthält keine GeoJSON-Features.")

    return features


def update_if_not_null(playground, field_name, value):
    if value is None:
        return False

    if getattr(playground, field_name) == value:
        return False

    setattr(playground, field_name, value)
    return True


def sync_feature(feature, organization):
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}

    raw_uuid = value_or_none(properties.get("uuid"))

    if not raw_uuid:
        return "skipped"

    try:
        playground_uuid = uuid.UUID(raw_uuid)
    except ValueError:
        return "skipped"

    name = value_or_none(properties.get("name"))

    playground = Playground.objects.filter(uuid=playground_uuid).first()
    created = False

    if playground is None:
        if not name:
            return "skipped"

        playground = Playground(
            uuid=playground_uuid,
            organization=organization,
            name=name,
            slug=create_unique_slug(name, organization),
            is_active=True,
            public_visible=True,
        )
        created = True

    changed = False

    if not created and playground.organization_id != organization.id:
        return "skipped"

    if name:
        changed = update_if_not_null(playground, "name", name) or changed

    number = number_or_none(properties.get("nummer"))
    changed = update_if_not_null(playground, "number", number) or changed

    street_name = value_or_none(properties.get("streetName"))
    changed = update_if_not_null(playground, "street_name", street_name) or changed

    house_number = value_or_none(properties.get("houseNo"))
    changed = update_if_not_null(playground, "house_number", house_number) or changed

    address = build_address(street_name, house_number)
    changed = update_if_not_null(playground, "address", address) or changed

    coordinates = geometry.get("coordinates") or []

    if len(coordinates) >= 2:
        x = decimal_or_none(coordinates[0])
        y = decimal_or_none(coordinates[1])

        changed = update_if_not_null(playground, "longitude", x) or changed
        changed = update_if_not_null(playground, "latitude", y) or changed

    if created or changed:
        if created and not playground.slug:
            playground.slug = create_unique_slug(playground.name, organization)

        playground.full_clean()
        playground.save()

    if created:
        return "created"

    if changed:
        return "updated"

    return "unchanged"


def sync_playgrounds_from_url(url, organization):
    features = fetch_feature_collection(url)

    result = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
        "total": len(features),
    }

    for feature in features:
        if not isinstance(feature, dict):
            result["skipped"] += 1
            continue

        status = sync_feature(feature, organization)
        result[status] += 1

    return result
