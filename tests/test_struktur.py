"""Struktur des Blueprints: Aufbau, Eingaben, Selektoren, Zweige.

Diese Tests fangen Fehler ab, die Home Assistant erst beim Laden meldet –
etwa eine Eingabe, die referenziert aber nicht definiert ist.
"""

from __future__ import annotations

import pytest

from conftest import BLUEPRINT, all_inputs, find_input, input_names

SEKTIONEN = [
    "basis", "app_uhrzeit", "app_datum", "app_temperatur", "app_pv",
    "app_waermepumpe", "app_fenster", "app_eigene",
    "darstellung", "nachrichten", "anwesenheit",
]
# Nur diese Abschnitte sind beim Öffnen aufgeklappt.
AUFGEKLAPPT = ["basis", "app_uhrzeit"]
ZWEIGE = [
    "App-Rotation",
    "Benachrichtigung anzeigen",
    "Anwesend: einschalten",
    "Abwesend: Anzeige aus",
    "Abwesend: Strom trennen",
]
TRIGGER_IDS = ["rotation", "nachricht", "eingabefeld", "anwesend", "anzeige_aus", "strom_aus"]


def test_datei_existiert():
    assert BLUEPRINT.is_file(), f"Blueprint fehlt: {BLUEPRINT}"


def test_pflichtfelder_vorhanden(blueprint):
    bp = blueprint["blueprint"]
    assert bp["domain"] == "automation"
    assert bp["name"]
    assert bp["description"]
    assert blueprint["mode"] == "queued", "Nachrichten und Rotation müssen sich einreihen können"
    assert blueprint["max"] >= 10


def test_sektionen_vollstaendig(blueprint):
    assert list(blueprint["blueprint"]["input"]) == SEKTIONEN


def test_nur_pflichtabschnitte_sind_aufgeklappt(blueprint):
    """Beim Öffnen soll man nicht von 53 Feldern erschlagen werden.

    Aufgeklappt sind nur die Grundeinstellungen und die Uhrzeit – zusammen
    sechs Felder. Alles andere ist optional und wird bei Bedarf ausgeklappt.
    """
    offen = [k for k, s in blueprint["blueprint"]["input"].items() if not s["collapsed"]]
    assert offen == AUFGEKLAPPT


def test_jeder_abschnitt_hat_namen_und_symbol(blueprint):
    for key, sektion in blueprint["blueprint"]["input"].items():
        assert sektion.get("name"), f"Abschnitt {key} ohne Namen"
        assert sektion.get("icon", "").startswith("mdi:"), f"Abschnitt {key} ohne Symbol"
        assert "collapsed" in sektion, f"Abschnitt {key} ohne collapsed"


def test_optionale_abschnitte_sind_als_solche_benannt(blueprint):
    """Wer den Blueprint öffnet, soll sofort sehen, was Pflicht ist."""
    for key, sektion in blueprint["blueprint"]["input"].items():
        if key.startswith("app_") and key != "app_uhrzeit":
            assert "(optional)" in sektion["name"], f"{key}: Hinweis fehlt"


def test_jede_eingabe_wird_benutzt(blueprint):
    definiert = set(all_inputs(blueprint))
    benutzt = input_names()
    assert not (benutzt - definiert), f"referenziert, aber nicht definiert: {benutzt - definiert}"
    assert not (definiert - benutzt), f"definiert, aber ungenutzt: {definiert - benutzt}"


def test_nur_matrix_ist_pflicht(blueprint):
    """Alles außer der Matrix selbst muss einen Standardwert haben."""
    ohne_default = [n for n, f in all_inputs(blueprint).items() if "default" not in f]
    assert ohne_default == ["wled_light"]


def test_jede_eingabe_hat_name_und_selector(blueprint):
    for name, feld in all_inputs(blueprint).items():
        assert feld.get("name"), f"{name} ohne Anzeigename"
        assert feld.get("selector"), f"{name} ohne Selektor"


def test_matrix_selektor_filtert_auf_wled(blueprint):
    feld = find_input(blueprint, "wled_light")
    filt = feld["selector"]["entity"]["filter"][0]
    assert filt == {"integration": "wled", "domain": "light"}


def test_stromschalter_kann_keine_lampe_sein(blueprint):
    """Sonst könnte man versehentlich die Matrix selbst als Stromschalter wählen."""
    feld = find_input(blueprint, "power_switch")
    domains = {f["domain"] for f in feld["selector"]["entity"]["filter"]}
    assert "light" not in domains
    assert domains == {"switch", "input_boolean"}


def test_trigger_ids(blueprint):
    assert [t["id"] for t in blueprint["triggers"]] == TRIGGER_IDS


def test_optionale_trigger_entitaeten_haben_leere_liste_als_standard(blueprint):
    """Ein leerer Text ist kein gültiges entity_id.

    Steht bei einer optionalen Entitäts-Eingabe ``default: ""`` und wird sie in
    einem Trigger verwendet, lehnt Home Assistant das Speichern der Automation
    ab: "Entity is neither a valid entity ID nor a valid UUID". Der Standard
    muss deshalb eine leere Liste sein.
    """
    in_triggern = {
        name
        for t in blueprint["triggers"]
        if isinstance(t.get("entity_id"), tuple) and t["entity_id"][0] == "INPUT"
        for name in [t["entity_id"][1]]
    }
    assert in_triggern, "Test greift ins Leere – keine !input-Entität in den Triggern"

    felder = all_inputs(blueprint)
    falsch = [
        name
        for name in in_triggern
        if "default" in felder[name] and felder[name]["default"] == ""
    ]
    assert not falsch, f"leerer Text als Standard, muss [] sein: {falsch}"


def test_optionale_entitaeten_werden_normalisiert(blueprint, variables):
    """Wegen ``default: []`` können diese Eingaben Liste oder Text sein.

    Der Blueprint muss sie auf Text normalisieren, sonst vergleicht der Rest
    eine Liste mit '' und die Prüfungen laufen ins Leere.
    """
    for name in ("presence", "text_helper"):
        vorlage = variables[name]
        assert "is string" in str(vorlage), f"{name} wird nicht normalisiert"


def test_zweige_vorhanden(branches):
    assert list(branches) == ZWEIGE


@pytest.mark.parametrize("zweig", ZWEIGE)
def test_jeder_zweig_prueft_seinen_trigger(branches, zweig):
    bedingungen = str(branches[zweig]["conditions"])
    assert "condition: trigger" in bedingungen or "'condition': 'trigger'" in bedingungen


@pytest.mark.parametrize(
    "zweig",
    ["App-Rotation", "Benachrichtigung anzeigen"],
)
def test_sendende_zweige_pruefen_die_adresse(branches, zweig):
    """Ohne IP darf kein REST-Aufruf losgehen."""
    assert "host != ''" in str(branches[zweig]["conditions"])


@pytest.mark.parametrize(
    "zweig",
    ["App-Rotation", "Benachrichtigung anzeigen"],
)
def test_sendende_zweige_achten_auf_anwesenheit(branches, zweig):
    assert "presence == ''" in str(branches[zweig]["conditions"])


def test_rotation_schaltet_matrix_nicht_ein(branches):
    """Eine ausgeschaltete Matrix soll ausgeschaltet bleiben."""
    bedingungen = str(branches["App-Rotation"]["conditions"])
    assert "is_state(light_entity, 'on')" in bedingungen
    schritte = str(branches["App-Rotation"]["sequence"])
    assert "light.turn_on" not in schritte


def test_nachricht_schaltet_matrix_ein(branches):
    """Eine Benachrichtigung darf die Matrix kurz aufwecken."""
    assert "light.turn_on" in str(branches["Benachrichtigung anzeigen"]["sequence"])


def test_interval_werte_passen_zum_trigger(blueprint):
    """Jede Auswahl muss ein gültiges time_pattern für Sekunden sein."""
    optionen = find_input(blueprint, "interval")["selector"]["select"]["options"]
    for opt in optionen:
        wert = opt["value"]
        assert wert == "0" or (wert.startswith("/") and 0 < int(wert[1:]) <= 59)


def _auswahlwerte(feld) -> set[str]:
    return {o["value"] if isinstance(o, dict) else o
            for o in feld["selector"]["select"]["options"]}


def test_schriften_konsistent(blueprint, variables):
    """Jede anwählbare Schrift muss in der Umrechnungstabelle stehen."""
    feld = find_input(blueprint, "font")
    assert _auswahlwerte(feld) == set(variables["fonts"])


@pytest.mark.parametrize(
    "feld",
    ["time_font", "date_font", "temp_font", "pv_font", "hp_font", "window_font"],
)
def test_schriftauswahl_pro_app(blueprint, variables, feld):
    """Pro App: dieselben Schriften plus "" für "wie eingestellt"."""
    eingabe = find_input(blueprint, feld)
    assert eingabe["default"] == "", "Standard muss die globale Schrift erben"
    assert _auswahlwerte(eingabe) == set(variables["fonts"]) | {""}


def test_schriftbeschriftung_nennt_den_wled_regler(blueprint):
    """WLED zeigt im Schieberegler 0, 64 und 128 statt "4x6" und so weiter.

    Ohne diese Zahlen in der Beschriftung lässt sich nicht zuordnen, was in der
    WLED-Oberfläche steht.
    """
    feld = find_input(blueprint, "font")
    beschriftungen = " ".join(o["label"] for o in feld["selector"]["select"]["options"])
    for wert in ("0", "64", "128"):
        assert f"Regler {wert}" in beschriftungen


def test_schriftwerte_entsprechen_wled(variables):
    """Die Werte sind durch WLED vorgegeben: Schieberegler c2 wählt die Schrift.

    0 = 4x6, 64 = 5x8, 128 = 6x8. Diese Zahlen dürfen sich nicht verschieben,
    sonst zeigt die Matrix eine andere Schrift als ausgewählt.
    """
    assert variables["fonts"] == {"4x6": 0, "5x8": 64, "6x8": 128}


def test_effekt_id_ist_eine_feste_zahl(blueprint):
    """Die Effekt-ID wird eingetragen, nicht erraten.

    Ein früherer Versuch, sie aus ``effect_list`` der WLED-Integration
    abzuleiten, war falsch: Home Assistant liefert diese Liste nicht in der
    Reihenfolge der Effekt-IDs der Firmware. Das Ergebnis war ein anderer
    Effekt, ohne Fehlermeldung. Verlässlich ist nur ``/json/eff``.
    """
    feld = find_input(blueprint, "effect_id")
    assert feld["default"] == 122
    assert "number" in feld["selector"]


def test_keine_effektlisten_erkennung_mehr(blueprint):
    """Schutz vor einem Rückfall: effect_list darf nicht wieder auftauchen."""
    quelltext = BLUEPRINT.read_text(encoding="utf-8")
    assert "effect_list" not in quelltext


# ==========================================================================
# Die Testkonfiguration für den Home-Assistant-Job in der CI
# ==========================================================================
def _fixture_automationen():
    import yaml as _yaml

    pfad = BLUEPRINT.parent.parent.parent.parent / "tests" / "fixtures" / "automations.yaml"
    return {a["id"]: a["use_blueprint"]["input"] for a in _yaml.safe_load(pfad.read_text("utf-8"))}


def test_fixture_kennt_nur_echte_eingaben(blueprint):
    """Verhindert, dass die CI-Konfiguration veraltet.

    Wird eine Eingabe umbenannt oder entfernt, verweist die Testautomation ins
    Leere und der Home-Assistant-Job schlägt fehl – aber erst auf GitHub.
    Dieser Test fängt es schon lokal ab.
    """
    echt = set(all_inputs(blueprint))
    for kennung, eingaben in _fixture_automationen().items():
        unbekannt = set(eingaben) - echt
        assert not unbekannt, f"Automation '{kennung}' nutzt unbekannte Eingaben: {unbekannt}"


def test_fixture_deckt_alle_eingaben_ab(blueprint):
    """Die Automation "vollstaendig" muss jede Eingabe belegen.

    Nur dann prüft Home Assistant in der CI wirklich alle Selektoren.
    """
    echt = set(all_inputs(blueprint))
    fehlen = echt - set(_fixture_automationen()["vollstaendig"])
    assert not fehlen, f"in der Testautomation nicht belegt: {fehlen}"


def test_fixture_hat_einen_minimalfall():
    """Nur die Pflichteingabe – das deckt den Fall ab, der zuletzt gescheitert ist."""
    assert list(_fixture_automationen()["minimal"]) == ["wled_light"]


def test_keine_veralteten_abschnittsnummern(blueprint):
    """Die Abschnitte heißen seit dem Umbau nach Namen, nicht nach Nummern.

    Ein Verweis wie "siehe Abschnitt 3" wird beim Umsortieren falsch, ohne dass
    es jemandem auffällt.
    """
    texte = " ".join(
        str(feld.get("description", "")) + " " + str(feld.get("name", ""))
        for feld in all_inputs(blueprint).values()
    )
    for nummer in range(1, 12):
        assert f"Abschnitt {nummer}" not in texte, f'Verweis auf "Abschnitt {nummer}" gefunden'


def test_stolperfallen_sind_erklaert(blueprint):
    """Felder, an denen im Betrieb schon jemand hängengeblieben ist.

    Bei der Wärmepumpe führten ein falsch gesetztes Vorzeichen und die
    Bereitschafts-Schwelle dazu, dass die App gar nicht erschien – ohne
    Fehlermeldung. Die Beschreibungen müssen darauf hinweisen.
    """
    for name, stichwort in [
        ("hp_invert", "NEGATIVE"),
        ("hp_only_when_running", "ERSCHEINT DIE APP NICHT"),
        ("hp_sensor", "erscheint die App nicht"),
        ("pv_only_when_producing", "negative"),
    ]:
        beschreibung = find_input(blueprint, name).get("description", "")
        assert stichwort in beschreibung, f"{name}: Hinweis auf '{stichwort}' fehlt"
