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
* SQLite für lokale Entwicklung
* vorbereitet für späteren Wechsel auf PostgreSQL / PostGIS
* Leaflet für die öffentliche Kartenansicht
* Bootstrap für einfache responsive Oberflächen
* Pillow für Bildverarbeitung
* `ImageAsset`-Modell zur Speicherung von Bildern in der Datenbank

---

## Lokales Setup

### 1. Repository klonen

```bash
git clone <repo-url>
cd spielplatz-atlas
```

### 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Datenbank migrieren

```bash
python manage.py migrate
```

### 5. Superuser erstellen

```bash
python manage.py createsuperuser
```

### 6. Standardkatalog importieren

```bash
python manage.py seed_standard_catalogs_from_json
```

### 7. Entwicklungsserver starten

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

### Import des Standardkatalogs

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
* SQLite-fähig für den Einstieg
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
