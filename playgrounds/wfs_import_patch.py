import urllib.parse

from . import quartier_import


def build_wfs_getfeature_url(endpoint, feature_type_name, output_format=None):
    parsed = urllib.parse.urlparse(endpoint)
    raw_query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))

    service = "WFS"
    version = None

    for key, value in raw_query.items():
        key_lower = key.lower()
        if key_lower == "service" and value:
            service = value
        elif key_lower == "version" and value:
            version = value

    query = {
        key: value
        for key, value in raw_query.items()
        if key.lower() not in {
            "service",
            "request",
            "typename",
            "typenames",
            "outputformat",
        }
    }

    query.update({
        "service": service,
        "request": "GetFeature",
        "typeName": feature_type_name,
    })

    if version:
        query["version"] = version

    if output_format:
        query["outputFormat"] = output_format

    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


quartier_import.build_wfs_getfeature_url = build_wfs_getfeature_url
