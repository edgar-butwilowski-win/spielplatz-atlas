TRANSLATIONS = {
    "de": {
        "Replace playground image": "Spielplatzbild ersetzen",
        "Replace image": "Bild ersetzen",
        "Upload image": "Bild hochladen",
        "Rotate image by 90\u00b0": "Bild um 90\u00b0 drehen",
        "The current preview image comes from a play equipment item. It can be rotated there.": "Das aktuelle Vorschaubild stammt von einem Spielgeraet. Es kann dort gedreht werden.",
        "Equipment on this playground.": "Spielgeraete auf diesem Spielplatz.",
        "Defect with safety risk": "Mangel mit Sicherheitsrisiko",
        "Defect without safety risk": "Mangel ohne Sicherheitsrisiko",
        "In operation": "In Betrieb",
        "Renovation pending": "Sanierung ausstehend",
        "Due soon": "Bald faellig",
        "Without assignment": "Ohne Zuweisung",
        "On time": "Fristgerecht",
        "All assignments": "Alle Zuweisungen",
        "Assigned": "Zugewiesen",
    },
    "fr": {
        "Replace playground image": "Remplacer l image de la place de jeux",
        "Replace image": "Remplacer l image",
        "Upload image": "Televerser l image",
        "Rotate image by 90\u00b0": "Faire pivoter l image de 90\u00b0",
        "The current preview image comes from a play equipment item. It can be rotated there.": "L image d apercu actuelle provient d un equipement de jeu. Elle peut y etre pivotee.",
        "Equipment on this playground.": "Equipements presents sur cette place de jeux.",
        "Defect with safety risk": "Defaut avec risque de securite",
        "Defect without safety risk": "Defaut sans risque de securite",
        "In operation": "En service",
        "Renovation pending": "Renovation en attente",
        "Due soon": "Bientot echu",
        "Without assignment": "Sans attribution",
        "On time": "Dans les delais",
        "All assignments": "Toutes les attributions",
        "Assigned": "Attribue",
    },
    "it": {
        "Replace playground image": "Sostituire l immagine del parco giochi",
        "Replace image": "Sostituire immagine",
        "Upload image": "Caricare immagine",
        "Rotate image by 90\u00b0": "Ruotare l immagine di 90\u00b0",
        "The current preview image comes from a play equipment item. It can be rotated there.": "L immagine di anteprima attuale proviene da un attrezzatura da gioco. Puo essere ruotata li.",
        "Equipment on this playground.": "Attrezzature presenti in questo parco giochi.",
        "Defect with safety risk": "Difetto con rischio per la sicurezza",
        "Defect without safety risk": "Difetto senza rischio per la sicurezza",
        "In operation": "In esercizio",
        "Renovation pending": "Risanamento in sospeso",
        "Due soon": "In scadenza a breve",
        "Without assignment": "Senza assegnazione",
        "On time": "Nei termini",
        "All assignments": "Tutte le assegnazioni",
        "Assigned": "Assegnato",
    },
    "rm": {
        "Replace playground image": "Remplazzar il maletg da la plazza da gieu",
        "Replace image": "Remplazzar il maletg",
        "Upload image": "Chargiar si il maletg",
        "Rotate image by 90\u00b0": "Girar il maletg per 90\u00b0",
        "The current preview image comes from a play equipment item. It can be rotated there.": "Il maletg da prevista actual deriva dad in indriz da gieu. El po vegnir gira la.",
        "Equipment on this playground.": "Indrizs da gieu sin questa plazza da gieu.",
        "Defect with safety risk": "Mangel cun ristg da segirezza",
        "Defect without safety risk": "Mangel senza ristg da segirezza",
        "In operation": "En funcziun",
        "Renovation pending": "Sanaziun pendenta",
        "Due soon": "Scroda bainprest",
        "Without assignment": "Senza attribuziun",
        "On time": "Entaifer il termin",
        "All assignments": "Tut las attribuziuns",
        "Assigned": "Attribui",
    },
}


_installed = False


def _language_code():
    from django.utils import translation

    language = translation.get_language() or "en"
    return language.split("-", 1)[0].lower()


def install():
    global _installed
    if _installed:
        return

    from django.utils import translation
    from django.utils.translation import trans_real

    original_gettext = trans_real.gettext
    original_ngettext = trans_real.ngettext

    def gettext(message):
        translated = original_gettext(message)
        if translated != message:
            return translated
        return TRANSLATIONS.get(_language_code(), {}).get(message, translated)

    def ngettext(singular, plural, number):
        translated = original_ngettext(singular, plural, number)
        original = singular if number == 1 else plural
        if translated != original:
            return translated
        message = singular if number == 1 else plural
        return TRANSLATIONS.get(_language_code(), {}).get(message, translated)

    trans_real.gettext = gettext
    trans_real.ngettext = ngettext
    translation.gettext = gettext
    translation.ngettext = ngettext
    translation._trans.gettext = gettext
    translation._trans.ngettext = ngettext
    _installed = True
