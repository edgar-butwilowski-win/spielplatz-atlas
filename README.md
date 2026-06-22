# SpielplatzAtlas

**SpielplatzAtlas** ist eine mandantenfähige WebApp zur Verwaltung, Kontrolle und öffentlichen Information von Spielplätzen.

Die Anwendung richtet sich einerseits an Städte, Gemeinden und andere öffentliche Betreiber von Spielplätzen. Andererseits bietet sie Bürgerinnen und Bürgern eine öffentliche Übersicht über Spielplätze, Spielgeräte und freigegebene Informationen zum Pflegestand.

Der Prüfkatalog ist als **Prüfkatalog auf Basis von SN EN 1176/1177** modelliert und wird als versionierter Anbieter-Standardkatalog geführt.

---

## Ziel der Anwendung

SpielplatzAtlas unterstützt Betreiber dabei, Spielplätze strukturiert zu erfassen, Kontrollprozesse nachvollziehbar zu dokumentieren und ausgewählte Informationen öffentlich bereitzustellen.

Die App verfolgt einen Dual-Use-Ansatz:

- **Öffentliche Spielplatzkarte** für Bürgerinnen und Bürger
- **Interne Fachanwendung** für Verwaltung, Kontrolle, Pflege und Betrieb

Eingeloggte Mitarbeitende sehen dieselbe Grundsicht wie die Öffentlichkeit, erhalten aber zusätzliche Funktionen, zum Beispiel zum Erfassen von Kontrollen und Stammdaten.

---

## Hauptfunktionen

### Öffentliche Funktionen

- öffentliche Startseite mit Kartenansicht
- Anzeige öffentlich sichtbarer Spielplätze
- Detailseite pro Spielplatz
- Anzeige öffentlich sichtbarer Spielgeräte
- Anzeige freigegebener Mängel und geplanter Instandsetzungen
- mandantenabhängige Farben und Organisationseinstellungen

### Interne Funktionen

- Mandantenfähigkeit für mehrere Organisationen
- Registrierung neuer Organisationen über Organisationsanfragen
- Freigabe oder Ablehnung neuer Organisationen durch Superadmin
- Organisations-Admins mit eigener Organisation
- Verwaltung von Spielplätzen
- Verwaltung von Spielgeräten
- Verwaltung von Fallschutzflächen / Böden
- Verwaltung von Zusatzausstattung
- Upload eines optionalen Hauptfotos pro Spielplatz
- Upload eines optionalen Hauptfotos pro Spielgerät
- Erfassung von Kontrollen
- automatische Erzeugung von Prüfbereichen und Prüfpunkten
- Mängelerfassung mit Sicherheitsrisiko-Kennzeichnung
- öffentliche Freigabe ausgewählter Mängelinformationen
- Import von Quartieren über GeoJSON oder WFS und räumliche Zuordnung per SpatiaLite

---

## Fachliches Modell

Eine Kontrolle ist als Begehung eines Spielplatzes modelliert.

```text
Inspection
= Kontrollvorgang / Begehung eines Spielplatzes

InspectionScope
= Prüfbereich innerhalb einer Kontrolle

InspectionAnswer
= konkrete Antwort zu einem Prüfkriterium innerhalb eines Prüfbereichs
````

Aktuell unterstützte Prüfbereich-Typen:

```text
playground  = Allgemeine Spielplatzprüfung
equipment   = Spielgerät
surface     = Fallschutzfläche / Boden
accessory   = Zusatzausstattung
```

Damit können allgemeine Prüfpunkte, Spielgeräte, Fallschutzflächen und Zusatzausstattung fachlich getrennt geprüft werden.

---

## Prüfkatalog auf Basis von SN EN 1176/1177

SpielplatzAtlas enthält einen globalen Anbieter-Standardkatalog.

Dieser umfasst aktuell:

* Spielgerätearten
* Prüfkriterien
* Anwendbarkeiten von Prüfkriterien auf Prüfbereiche

Der Katalog wird nicht als kundenspezifischer Import verstanden, sondern als versionierter App-Standard.

Globale Standardwerte sind geschützt:

```text
organization = leer
is_standard = ja
is_locked = ja
standard_version = SN-EN-1176-1177-v1
```

Organisationen können zusätzlich lokale Ergänzungen erfassen. Globale Standards bleiben dabei sichtbar, aber nicht direkt veränderbar.

---

## Technischer Stack

* Python
* Django
* SQLite mit SpatiaLite für lokale Entwicklung und räumliche Abfragen
* GeoDjango für Geometriefelder und Spatial Queries
* vorbereitet für späteren Wechsel auf PostgreSQL / PostGIS
* Leaflet für die öffentliche Kartenansicht
* Bootstrap für einfache responsive Oberflächen
* Pillow für Bildverarbeitung
* `ImageAsset`-Modell zur Speicherung von Bildern in der Datenbank

---

## Zentrales Übersetzungskonzept

SpielplatzAtlas verwendet für die gesamte WebApp das zentrale Internationalisierungs- und Übersetzungskonzept von Django. Übersetzbare Texte werden im Code explizit markiert und anschliessend über die Django-Sprachkataloge gepflegt.

In Templates werden dafür `{% trans %}` und `{% blocktrans %}` verwendet. In Python-Code werden übersetzbare Texte mit `_()` beziehungsweise `gettext_lazy()` markiert, insbesondere bei Model-Choices, Formularlabels, Meldungen und statischen Anzeige-Texten.

Andere parallele Übersetzungskonzepte sind in diesem Projekt nicht erwünscht. Insbesondere sollen keine separaten Mapping-Tabellen, manuellen Sprachumschalter, dynamischen Template-Übersetzungen bereits berechneter Werte oder eigene Übersetzungs-Hilfsfunktionen neben Django i18n aufgebaut werden. Neue übersetzbare Texte sollen so eingeführt werden, dass sie mit `makemessages` gefunden und in den bestehenden `locale/*/LC_MESSAGES/django.po`-Katalogen gepflegt werden können.

Bei Neuentwicklungen von UI-Elementen sowie bei Anpassungen bestehender UI-Elemente wird von Entwicklerinnen und Entwicklern erwartet, dass zeitgleich passende Übersetzungen für das betreffende UI-Element in allen fünf unterstützten Sprachen nachgeführt werden: English, Deutsch, Französisch, Italienisch und Rätoromanisch.

---

## Zentrales Logging

SpielplatzAtlas verwendet für technische Logmeldungen das zentrale Django-Logging über `system_logging`. Sobald die Datenbanktabelle `system_logging.LogEntry` erreichbar ist, werden Logmeldungen in dieser Tabelle gespeichert und im Django-Admin im Bereich **Logging** angezeigt. Während des frühen Aufstartens, wenn die Datenbanktabelle noch nicht erreichbar ist, fällt das Logging auf die Konsole zurück.

Neue technische Logmeldungen werden immer über das Standardmodul `logging` von Python erzeugt. Beispiel:

```python
import logging

logger = logging.getLogger(__name__)


def import_quartiere(organization):
    logger.info(
        "Quartierimport für Organisation %s gestartet.",
        organization.pk,
    )

    try:
        # Fachlogik ausführen
        pass
    except Exception:
        logger.exception(
            "Quartierimport für Organisation %s fehlgeschlagen.",
            organization.pk,
        )
        raise
```

Bei der Weiterentwicklung ist zwingend darauf zu achten, dass für technisches Logging ausschliesslich dieses bestehende Logging-System verwendet wird. Parallele Logging-Modelle, eigene Logtabellen, direkte technische `print`-Ausgaben oder andere eigenständige Logging-Strukturen sind nicht zulässig. Fachliche Statusfelder, zum Beispiel Zustellstatus von Benachrichtigungen, dürfen bestehen bleiben; technische Fehler und Diagnoseinformationen müssen aber zusätzlich über `logging` protokolliert werden.

---

## Lokales Setup

### 1. Repository klonen

```bash
git clone <repo-url>
cd spielplatz-atlas
```

### 2. Systemabhängigkeiten für SpatiaLite installieren

Auf Debian/Ubuntu wird für GeoDjango mit SQLite die SpatiaLite-Erweiterung benötigt:

```bash
sudo apt install libsqlite3-mod-spatialite
```

Falls die Erweiterung nicht automatisch unter `mod_spatialite` gefunden wird, kann der Pfad über eine Umgebungsvariable gesetzt werden:

```bash
export SPATIALITE_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/mod_spatialite.so
```

Auf anderen Systemen muss `SPATIALITE_LIBRARY_PATH` entsprechend auf die installierte SpatiaLite-Bibliothek zeigen.

### Umgebung im WebApp-Titel

Die Umgebung wird aus der `.env`-Datei im Projekt-Root gelesen. Verwende dafür bevorzugt `DJANGO_ENVIRONMENT`. Zulässige Werte sind `DEV`, `TEST` und `PROD`. In `DEV` und `TEST` ergänzt die WebApp den Browser-Titel automatisch mit `[DEV]` beziehungsweise `[TEST]` und zeigt zusätzlich ein sichtbares Badge `DEV` beziehungsweise `TEST` neben dem WebApp-Namen an. In `PROD` bleibt der Titel unverändert und es wird kein Badge angezeigt.

Beispiel für `.env`:

```env
DJANGO_ENVIRONMENT=DEV
```

Falls bestehende Deployments bereits `ENVIRONMENT`, `APP_ENV` oder `DJANGO_ENV` verwenden, werden diese Variablen ebenfalls akzeptiert. Ohne explizite Angabe gilt bei `DJANGO_DEBUG=True` automatisch `DEV`, sonst `PROD`.

### 3. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Python-Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5. Datenbank migrieren

```bash
python manage.py migrate
```

Beim Migrieren wird die bestehende SQLite-Datenbank durch das GeoDjango-SpatiaLite-Backend verwendet. Die Migrationen legen räumliche Geometriespalten an und befüllen sie aus den bestehenden LV95-Koordinaten sowie aus importierten Quartier-GeoJSON-Geometrien.

### 6. Superuser erstellen

```bash
python manage.py createsuperuser
```

### 7. Standardkatalog importieren

```bash
python manage.py seed_standard_catalogs_from_json
```

### 8. Entwicklungsserver starten

```bash
python manage.py runserver
```

Die Anwendung ist danach erreichbar unter:

```text
http://127.0.0.1:8000/
```

Der Admin-Bereich ist erreichbar unter:

```text
http://127.0.0.1:8000/admin/
```

---

## SpatiaLite und räumliche Daten

SpielplatzAtlas verwendet GeoDjango mit SpatiaLite. Die fachlichen LV95-Koordinatenfelder bleiben aus Kompatibilitätsgründen erhalten:

```text
longitude = LV95 X
latitude  = LV95 Y
```

Zusätzlich werden daraus räumliche Punktgeometrien mit SRID 2056 erzeugt:

```text
Playground.location
PlayEquipment.location
```

Quartiere werden weiterhin mit der importierten GeoJSON-Geometrie gespeichert, erhalten zusätzlich aber eine echte SpatiaLite-Geometrie:

```text
Quartier.geom      = importierte GeoJSON-Geometrie
Quartier.geometry  = MultiPolygonField, SRID 2056
```

Der Quartierimport erwartet weiterhin:

```text
Name      im Attribut Quartiername
Geometrie im Attribut geom
```

Bei GeoJSON wird zusätzlich das Standardfeld `geometry` akzeptiert. Nach dem Import werden Spielplätze über eine echte SpatiaLite-Punkt-in-Polygon-Abfrage dem passenden Quartier zugeordnet und das bestehende `district`-Feld wird aktualisiert.

---

## Standardkataloge im Verzeichnis `data/standard_catalogs`

Die fachlichen Anbieter-Standardkataloge liegen im Repo in einem entwicklungsfreundlichen, versionierbaren Format.

Empfohlene Struktur:

```text
data/
└── standard_catalogs/
    └── sn_en_1176_1177_v1/
        ├── equipment_types.json
        └── inspection_criteria.json
```

Die JSON-Dateien dienen als reproduzierbare Quelle für den initialen Standardkatalog.

### Zweck

`data/standard_catalogs` enthält keine produktiven Kundendaten, sondern fachliche Anbieter-Standards, die beim Setup einer neuen Entwicklungs- oder Testumgebung importiert werden können.

Vorteile:

* gut versionierbar
* im Git-Diff lesbar
* reproduzierbarer Import
* geeignet für lokale Entwicklung, CI/CD und spätere Deployments

Nach der Datenbankmigration kann der Standardkatalog importiert werden:

```bash
python manage.py seed_standard_catalogs_from_json
```

Der Import ist idempotent ausgelegt. Bereits vorhandene Einträge werden aktualisiert, nicht doppelt angelegt.

### Export des Standardkatalogs

Wenn der globale Standardkatalog in der Datenbank fachlich angepasst wurde, kann er wieder exportiert werden:

```bash
python manage.py export_standard_catalogs
```

Die exportierten Dateien landen unter:

```text
data/standard_catalogs/sn_en_1176_1177_v1/
```

---

## Wichtige Rollen

### Superadmin

Der Superadmin kann:

* Organisationen verwalten
* Organisationsanfragen genehmigen oder ablehnen
* globale Standardkataloge pflegen
* Spielgerätearten und Prüfkriterien global verwalten
* alle Mandanten sehen
* alle Daten bearbeiten

### Organisations-Admin

Ein Organisations-Admin kann:

* Daten der eigenen Organisation verwalten
* Spielplätze erfassen
* Spielgeräte erfassen
* Fallschutzflächen / Böden erfassen
* Zusatzausstattung erfassen
* Quartiere über GeoJSON oder WFS importieren
* Bilder hochladen
* Kontrollen erfassen
* lokale Ergänzungen zum Standardkatalog anlegen

Globale Standards sind für Organisations-Admins sichtbar, aber nicht änderbar.

### Kontrolleure

Kontrolleure sollen perspektivisch über eine eigene interne Kontrollmaske arbeiten und nicht primär über den Django-Admin.

---

## Bilder

Bilder werden über das Modell `ImageAsset` in der Datenbank gespeichert.

Aktuell unterstützt die Anwendung:

* optionales Hauptfoto pro Spielplatz
* optionales Hauptfoto pro Spielgerät
* Upload direkt im Adminformular
* Ausgabe über eine eigene Medien-Asset-View

Die Bilddaten werden nicht im Dateisystem abgelegt, sondern als Binärdaten in der Datenbank gespeichert.

---

## Öffentliche Mängelanzeige

Mängel können intern erfasst und optional öffentlich sichtbar gemacht werden.

Zusätzlich wird unterschieden:

```text
Sicherheitsrisiko: ja / nein
```

Bei einem Mangel ohne Sicherheitsrisiko kann öffentlich kommuniziert werden:

```text
An diesem Spielgerät ist ein Mangel bekannt.
Der Mangel stellt kein Sicherheitsrisiko dar.
Die Instandsetzung ist geplant.
```

So können Betreiber transparent informieren, ohne interne Kontrollnotizen vollständig öffentlich zu machen.

---

## Entwicklungsprinzipien

* mandantenfähige Architektur
* klare Trennung zwischen öffentlichen und internen Funktionen
* globale Anbieter-Standards statt beliebiger Tenant-Imports
* lokale Ergänzungen pro Organisation möglich
* responsives, ressourcenschonendes Webdesign
* SQLite-/SpatiaLite-fähig für den Einstieg
* spätere PostgreSQL-/PostGIS-Fähigkeit berücksichtigen
* Standardkataloge versionieren und reproduzierbar importieren

---

## Nächste geplante Ausbauschritte

Mögliche nächste Entwicklungsschritte:

* eigene mobile Kontrollmaske für Prüfantworten
* Bearbeitung von Prüfantworten ausserhalb des Django-Admins
* Mängelerfassung direkt aus einem Prüfpunkt heraus
* differenzierte Zuordnung von Prüfkriterien zu Spielgerätearten
* Export von Kontrollprotokollen als PDF
* bessere Foto-Vorschau im Admin
* Dashboard für offene Mängel und fällige Instandsetzungen
* spätere PostgreSQL/PostGIS-Migration
* erweiterte Kartenfunktionen
* Rollenmodell für Kontrolleure und Pflegepersonal

---

## Hinweis zur Normbezeichnung

Die Anwendung verwendet bewusst die Formulierung:

```text
Prüfkatalog auf Basis von SN EN 1176/1177
```

Damit wird ausgedrückt, dass der Katalog fachlich an diesen Normen ausgerichtet ist. Eine abschliessende rechtliche oder normative Zertifizierung wird dadurch nicht behauptet.

Der Standardkatalog sollte fachlich versioniert, geprüft und kontrolliert gepflegt werden.
