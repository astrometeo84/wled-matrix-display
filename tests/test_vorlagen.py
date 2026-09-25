"""Vorlagen aus dem Blueprint: IP-Erkennung, Einheiten, App-Liste."""

from __future__ import annotations

import pytest

from conftest import FakeHass, render

# ==========================================================================
# IP-Adresse
# ==========================================================================
class TestHost:
    def test_aus_der_integration(self, variables, hass, config):
        assert render(variables["host"], hass, **config) == "192.168.1.50"

    def test_handeintrag_hat_vorrang(self, variables, hass, config):
        cfg = {**config, "host_input": "  10.0.0.9  "}
        assert render(variables["host"], hass, **cfg) == "10.0.0.9"

    def test_https_und_schraegstrich_werden_entfernt(self, variables, config):
        hass = FakeHass().set("light.matrix", "on", configuration_url="https://wled.local/")
        assert render(variables["host"], hass, **config) == "wled.local"

    def test_ohne_adresse_leer(self, variables, config):
        """Leeres Ergebnis stoppt später den REST-Aufruf."""
        hass = FakeHass().set("light.matrix", "on")
        assert render(variables["host"], hass, **config) == ""


# ==========================================================================
# Einheiten W / kW
# ==========================================================================
class TestLeistung:
    @pytest.mark.parametrize(
        "wert,einheit,erwartet",
        [
            ("3.2", "kW", 3200.0),
            ("3200", "W", 3200.0),
            ("0.25", "kW", 250.0),
            ("0", "W", 0.0),
            ("unavailable", "W", 0.0),
        ],
    )
    def test_pv_umrechnung(self, variables, config, wert, einheit, erwartet):
        hass = FakeHass().set("sensor.pv", wert, unit_of_measurement=einheit)
        assert render(variables["pv_w"], hass, **config) == pytest.approx(erwartet)

    def test_ohne_sensor_null(self, variables, hass, config):
        cfg = {**config, "pv_sensor": ""}
        assert render(variables["pv_w"], hass, **cfg) == 0

    def test_fehlende_einheit_gilt_als_watt(self, variables, config):
        hass = FakeHass().set("sensor.pv", "750")
        assert render(variables["pv_w"], hass, **config) == pytest.approx(750.0)


class TestFenster:
    @pytest.mark.parametrize("offen,erwartet", [(0, 0), (1, 1), (3, 3)])
    def test_zaehlung(self, variables, config, offen, erwartet):
        hass = FakeHass()
        sensoren = [f"binary_sensor.f{i}" for i in range(3)]
        for i, e in enumerate(sensoren):
            hass.set(e, "on" if i < offen else "off")
        cfg = {**config, "window_sensors": sensoren}
        assert render(variables["windows_open"], hass, **cfg) == erwartet

    def test_ohne_sensoren(self, variables, hass, config):
        cfg = {**config, "window_sensors": []}
        assert render(variables["windows_open"], hass, **cfg) == 0


# ==========================================================================
# App-Liste
# ==========================================================================
class TestApps:
    def test_alle_apps_in_richtiger_reihenfolge(self, build_apps):
        apps, _ = build_apps()
        assert [a["text"] for a in apps] == [
            "#TIME",
            "#DATE",
            "7.3C",
            "PV 3.2 kW",
            "WP 820 W",
            "Speicher bei 57% ^",
            "2 Fenster offen",
        ]

    def test_uhr_ist_immer_erste_app(self, build_apps):
        apps, _ = build_apps()
        assert apps[0]["text"] == "#TIME"

    def test_uhr_abschaltbar(self, build_apps):
        apps, _ = build_apps(show_time=False)
        assert "#TIME" not in [a["text"] for a in apps]

    def test_nur_uhr_wenn_nichts_konfiguriert(self, build_apps):
        apps, _ = build_apps(
            show_date=False, temp_sensor="", pv_sensor="", hp_sensor="", bat_sensor="",
            window_sensors=[],
        )
        assert [a["text"] for a in apps] == ["#TIME"]

    def test_farben_werden_uebernommen(self, build_apps):
        apps, _ = build_apps(time_color=[1, 2, 3])
        assert apps[0]["color"] == [1, 2, 3]

    # --- PV ---------------------------------------------------------
    @pytest.mark.parametrize(
        "wert,einheit,text",
        [
            ("3.2", "kW", "PV 3.2 kW"),
            ("820", "W", "PV 820 W"),
            ("999", "W", "PV 999 W"),
            ("1000", "W", "PV 1.0 kW"),
        ],
    )
    def test_pv_formatierung(self, variables, config, build_apps, wert, einheit, text):
        apps, _ = build_apps()
        # eigener Haushalt nur für diesen Fall
        hass = FakeHass().set("sensor.pv", wert, unit_of_measurement=einheit)
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "hp_sensor": "", "window_sensors": []}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        cfg["hp_w"] = 0
        cfg["windows_open"] = 0
        apps = render(variables["apps"], hass, **cfg)
        assert apps[0]["text"] == text

    @pytest.mark.parametrize(
        "watt,farbe",
        [(100, [255, 60, 0]), (800, [255, 200, 0]), (3000, [0, 255, 0])],
    )
    def test_pv_ampelfarben(self, variables, config, watt, farbe):
        hass = FakeHass().set("sensor.pv", str(watt), unit_of_measurement="W")
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "hp_sensor": "", "window_sensors": [], "hp_w": 0, "windows_open": 0}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        apps = render(variables["apps"], hass, **cfg)
        assert apps[0]["color"] == farbe

    def test_pv_nachts_ausgeblendet(self, variables, config):
        hass = FakeHass().set("sensor.pv", "0", unit_of_measurement="W")
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "hp_sensor": "", "window_sensors": [], "hp_w": 0, "windows_open": 0}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        assert render(variables["apps"], hass, **cfg) == []

    def test_pv_nachts_sichtbar_wenn_gewuenscht(self, variables, config):
        hass = FakeHass().set("sensor.pv", "0", unit_of_measurement="W")
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "hp_sensor": "", "window_sensors": [], "hp_w": 0, "windows_open": 0,
               "pv_only": False}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        apps = render(variables["apps"], hass, **cfg)
        assert apps[0]["text"] == "PV 0 W"

    # --- Wärmepumpe -------------------------------------------------
    def test_wp_unter_schwelle_ausgeblendet(self, build_apps, hass):
        hass.set("sensor.wp", "40", unit_of_measurement="W")
        apps, _ = build_apps()
        assert not [a for a in apps if a["text"].startswith("WP")]

    def test_wp_ueber_schwelle_sichtbar(self, build_apps, hass):
        hass.set("sensor.wp", "150", unit_of_measurement="W")
        apps, _ = build_apps()
        assert "WP 150 W" in [a["text"] for a in apps]

    # --- Fenster ----------------------------------------------------
    @pytest.mark.parametrize(
        "offen,text",
        [(1, "1 Fenster offen"), (2, "2 Fenster offen"), (3, "3 Fenster offen")],
    )
    def test_fenster_singular_und_plural(self, variables, config, offen, text):
        hass = FakeHass()
        sensoren = [f"binary_sensor.f{i}" for i in range(3)]
        for i, e in enumerate(sensoren):
            hass.set(e, "on" if i < offen else "off")
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "pv_sensor": "", "hp_sensor": "", "window_sensors": sensoren,
               "pv_w": 0, "hp_w": 0}
        cfg["windows_open"] = render(variables["windows_open"], hass, **cfg)
        apps = render(variables["apps"], hass, **cfg)
        assert apps[0]["text"] == text

    def test_alle_zu_ausgeblendet(self, build_apps, hass):
        for e in ("binary_sensor.fenster_1", "binary_sensor.fenster_3"):
            hass.set(e, "off")
        apps, _ = build_apps()
        assert not [a for a in apps if "Fenster" in a["text"]]

    def test_alle_zu_sichtbar_wenn_gewuenscht(self, build_apps, hass):
        for e in ("binary_sensor.fenster_1", "binary_sensor.fenster_3"):
            hass.set(e, "off")
        apps, _ = build_apps(window_only=False)
        assert "Alle Fenster zu" in [a["text"] for a in apps]

    # --- Temperatur -------------------------------------------------
    def test_temperatur_gerundet(self, build_apps):
        apps, _ = build_apps()
        assert "7.3C" in [a["text"] for a in apps]

    @pytest.mark.parametrize("zustand", ["unknown", "unavailable"])
    def test_temperatur_ohne_wert_ausgeblendet(self, build_apps, hass, zustand):
        hass.set("sensor.aussentemperatur", zustand)
        apps, _ = build_apps()
        assert not [a for a in apps if a["text"].endswith("C")]

    # --- eigene Apps ------------------------------------------------
    def test_eigene_app_wird_angehaengt(self, build_apps):
        apps, _ = build_apps(custom_apps=[{"text": "Strom 28ct", "color": [255, 255, 0]}])
        assert apps[-1] == {"text": "Strom 28ct", "color": [255, 255, 0]}

    def test_eigene_app_mit_show_false_faellt_weg(self, build_apps):
        apps, _ = build_apps(
            custom_apps=[{"text": "sichtbar"}, {"text": "versteckt", "show": False}]
        )
        texte = [a["text"] for a in apps]
        assert "sichtbar" in texte and "versteckt" not in texte


# ==========================================================================
# Rotation
# ==========================================================================
def _durchlaufbeginn(anzahl: int, sekunden: int = 15) -> int:
    """Ein Zeitstempel, zu dem die Rotation bei der ersten App steht.

    Ein fester Zeitstempel passt nur zu einer bestimmten Anzahl Apps. Kommt
    eine App dazu, verschiebt sich der Startpunkt, und die Tests schlügen fehl,
    obwohl die Rotation stimmt.
    """
    durchlauf = anzahl * sekunden
    return (1758470400 // durchlauf) * durchlauf


class TestRotation:
    @pytest.mark.parametrize("pattern,sekunden", [("/10", 10), ("/15", 15), ("/30", 30), ("0", 60)])
    def test_intervall_umrechnung(self, hass, pattern, sekunden):
        vorlage = "{{ 60 if pattern == '0' else pattern[1:] | int }}"
        assert render(vorlage, hass, pattern=pattern) == sekunden

    def test_reihenfolge_ist_stabil_und_vollstaendig(self, build_apps, hass):
        apps, _ = build_apps()
        vorlage = "{{ apps[ ((ts | int) // (secs | int)) % (apps | count) ].text }}"
        start = _durchlaufbeginn(len(apps))
        gesehen = [
            render(vorlage, hass, apps=apps, ts=start + i * 15, secs=15)
            for i in range(len(apps))
        ]
        assert gesehen == [a["text"] for a in apps]

    def test_rotation_laeuft_rund(self, build_apps, hass):
        """Nach einem vollen Durchlauf beginnt es wieder bei der ersten App."""
        apps, _ = build_apps()
        vorlage = "{{ ((ts | int) // 15) % (apps | count) }}"
        beginn = _durchlaufbeginn(len(apps))
        start = render(vorlage, hass, apps=apps, ts=beginn)
        rum = render(vorlage, hass, apps=apps, ts=beginn + 15 * len(apps))
        assert start == rum == 0


# ==========================================================================
# Optionale Entitäten: Liste (nicht gesetzt) oder Text (gesetzt)
# ==========================================================================
class TestOptionaleEntitaeten:
    @pytest.mark.parametrize("name,roh", [("presence", "presence_raw"), ("text_helper", "text_helper_raw")])
    @pytest.mark.parametrize(
        "wert,erwartet",
        [([], ""), ("binary_sensor.praesenz", "binary_sensor.praesenz")],
    )
    def test_normalisierung(self, variables, hass, name, roh, wert, erwartet):
        assert render(variables[name], hass, **{roh: wert}) == erwartet


class TestSchriftProApp:
    """Jede App kann eine eigene Schrift bekommen.

    Steht sie auf "" (wie eingestellt), darf im App-Eintrag gar kein
    ``font`` auftauchen – dann greift in der Nutzlast die Schrift aus
    Abschnitt 3. Früher hatten einige Apps fest 5x8, wodurch die
    Schriftgröße beim App-Wechsel sichtbar sprang.
    """

    def test_ohne_auswahl_keine_schrift_im_eintrag(self, build_apps):
        apps, _ = build_apps()
        mit_schrift = [a["text"] for a in apps if "font" in a]
        assert not mit_schrift, f"legen ungefragt eine Schrift fest: {mit_schrift}"

    @pytest.mark.parametrize(
        "feld,text",
        [
            ("time_font", "#TIME"),
            ("date_font", "#DATE"),
            ("temp_font", "7.3C"),
            ("pv_font", "PV 3.2 kW"),
            ("hp_font", "WP 820 W"),
            ("bat_font", "Speicher bei 57% ^"),
            ("window_font", "2 Fenster offen"),
        ],
    )
    @pytest.mark.parametrize("schrift", ["4x6", "5x8", "6x8"])
    def test_auswahl_wirkt_nur_auf_ihre_app(self, build_apps, feld, text, schrift):
        apps, _ = build_apps(**{feld: schrift})
        treffer = [a for a in apps if a["text"] == text]
        assert treffer and treffer[0]["font"] == schrift
        andere = [a["text"] for a in apps if a["text"] != text and "font" in a]
        assert not andere, f"hat auch andere Apps verändert: {andere}"

    def test_eigene_app_darf_weiterhin_ueberschreiben(self, build_apps):
        apps, _ = build_apps(custom_apps=[{"text": "klein", "font": "4x6"}])
        assert apps[-1]["font"] == "4x6"


# ==========================================================================
# Wärmepumpe: Vorzeichen, Schwellen, Farbstufen
# ==========================================================================
class TestWaermepumpe:
    def _apps(self, variables, config, hass, **over):
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "pv_sensor": "", "window_sensors": [], "pv_w": 0, "windows_open": 0,
               "hp_sensor": "sensor.wp", **over}
        cfg["hp_w"] = render(variables["hp_w"], hass, **cfg)
        return render(variables["apps"], hass, **cfg)

    @pytest.mark.parametrize(
        "wert,einheit,erwartet",
        [("-820", "W", 820.0), ("820", "W", -820.0), ("-2.5", "kW", 2500.0)],
    )
    def test_vorzeichen_umkehren(self, variables, config, wert, einheit, erwartet):
        hass = FakeHass().set("sensor.wp", wert, unit_of_measurement=einheit)
        cfg = {**config, "hp_invert": True}
        assert render(variables["hp_w"], hass, **cfg) == pytest.approx(erwartet)

    def test_ohne_umkehren_unveraendert(self, variables, config):
        hass = FakeHass().set("sensor.wp", "-820", unit_of_measurement="W")
        assert render(variables["hp_w"], hass, **config) == pytest.approx(-820.0)

    def test_umgekehrter_sensor_wird_richtig_angezeigt(self, variables, config):
        """Der Praxisfall: Sensor zählt negativ, Anzeige soll positiv sein."""
        hass = FakeHass().set("sensor.wp", "-1500", unit_of_measurement="W")
        apps = self._apps(variables, config, hass, hp_invert=True)
        assert apps[0]["text"] == "WP 1.5 kW"
        assert apps[0]["color"] == config["hp_c_mid"]

    @pytest.mark.parametrize(
        "watt,stufe",
        [(40, "hp_c_idle"), (150, "hp_c_low"), (1200, "hp_c_mid"), (3000, "hp_c_high")],
    )
    def test_vier_farbstufen(self, variables, config, watt, stufe):
        hass = FakeHass().set("sensor.wp", str(watt), unit_of_measurement="W")
        apps = self._apps(variables, config, hass, hp_only=False)
        assert apps[0]["color"] == config[stufe]

    def test_eigene_schwellen_wirken(self, variables, config):
        hass = FakeHass().set("sensor.wp", "600", unit_of_measurement="W")
        apps = self._apps(variables, config, hass, hp_t_mid=500)
        assert apps[0]["color"] == config["hp_c_mid"], "600 W liegt über der neuen Schwelle 500"

    def test_bereitschaft_wird_ausgeblendet(self, variables, config):
        hass = FakeHass().set("sensor.wp", "40", unit_of_measurement="W")
        assert self._apps(variables, config, hass, hp_only=True) == []


# ==========================================================================
# PV-Speicher: Ladestand, fünf Farbstufen, Pfeil für Laden und Entladen
# ==========================================================================
class TestSpeicher:
    def _hass(self, soc="57.4", leistung="1200", einheit="W"):
        return (
            FakeHass()
            .set("sensor.speicher", soc, unit_of_measurement="%")
            .set("sensor.speicher_leistung", leistung, unit_of_measurement=einheit)
        )

    def _apps(self, variables, config, hass, **over):
        """Nur die Speicher-App, alle anderen abgeschaltet."""
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "pv_sensor": "", "hp_sensor": "", "window_sensors": [], "pv_w": 0,
               "hp_w": 0, "windows_open": 0, **over}
        cfg["bat_w"] = render(variables["bat_w"], hass, **cfg)
        return render(variables["apps"], hass, **cfg)

    def _app(self, variables, config, hass, **over):
        apps = self._apps(variables, config, hass, **over)
        assert len(apps) == 1, f"erwartet genau die Speicher-App, bekommen: {apps}"
        return apps[0]

    # --- Leistung ---------------------------------------------------
    @pytest.mark.parametrize(
        "wert,einheit,erwartet",
        [("1200", "W", 1200.0), ("1.2", "kW", 1200.0), ("-0.8", "kW", -800.0),
         ("unavailable", "W", 0.0)],
    )
    def test_leistung_in_watt(self, variables, config, wert, einheit, erwartet):
        hass = self._hass(leistung=wert, einheit=einheit)
        assert render(variables["bat_w"], hass, **config) == pytest.approx(erwartet)

    def test_ohne_leistungssensor_null(self, variables, config):
        cfg = {**config, "bat_power_sensor": ""}
        assert render(variables["bat_w"], self._hass(), **cfg) == 0

    @pytest.mark.parametrize("wert,erwartet", [("-1200", 1200.0), ("1200", -1200.0)])
    def test_vorzeichen_umkehren(self, variables, config, wert, erwartet):
        cfg = {**config, "bat_invert": True}
        hass = self._hass(leistung=wert)
        assert render(variables["bat_w"], hass, **cfg) == pytest.approx(erwartet)

    # --- Text und Pfeil ---------------------------------------------
    def test_laden_pfeil_nach_oben(self, variables, config):
        app = self._app(variables, config, self._hass(leistung="1200"))
        assert app["text"] == "Speicher bei 57% " + config["bat_up"]

    def test_entladen_pfeil_nach_unten(self, variables, config):
        app = self._app(variables, config, self._hass(leistung="-450"))
        assert app["text"] == "Speicher bei 57% " + config["bat_down"]

    def test_pfeile_sind_verschieden(self, config):
        """Sonst ließe sich Laden nicht von Entladen unterscheiden."""
        assert config["bat_up"] != config["bat_down"]

    def test_umgekehrter_sensor_zeigt_richtig(self, variables, config):
        """Der Praxisfall: Sensor meldet Laden als negative Zahl."""
        hass = self._hass(leistung="-1200")
        app = self._app(variables, config, hass, bat_invert=True)
        assert app["text"].endswith(config["bat_up"])

    @pytest.mark.parametrize("watt", ["0", "49", "-49"])
    def test_ruhe_ohne_pfeil(self, variables, config, watt):
        """Kleine Regelschwankungen sollen den Pfeil nicht flackern lassen."""
        app = self._app(variables, config, self._hass(leistung=watt))
        assert app["text"] == "Speicher bei 57%"

    @pytest.mark.parametrize("watt,richtung", [("50", "bat_up"), ("-50", "bat_down")])
    def test_ruheschwelle_ist_inklusiv(self, variables, config, watt, richtung):
        app = self._app(variables, config, self._hass(leistung=watt))
        assert app["text"].endswith(" " + config[richtung])

    def test_eigene_ruheschwelle(self, variables, config):
        hass = self._hass(leistung="300")
        assert self._app(variables, config, hass, bat_t_idle=500)["text"] == "Speicher bei 57%"

    def test_ruheschwelle_null_zeigt_bei_null_keinen_pfeil(self, variables, config):
        app = self._app(variables, config, self._hass(leistung="0"), bat_t_idle=0)
        assert app["text"] == "Speicher bei 57%"

    def test_ohne_leistungssensor_kein_pfeil(self, variables, config):
        app = self._app(variables, config, self._hass(), bat_power_sensor="")
        assert app["text"] == "Speicher bei 57%"

    @pytest.mark.parametrize("zustand", ["unknown", "unavailable"])
    def test_leistung_ohne_wert_kein_pfeil(self, variables, config, zustand):
        """Fällt nur der Leistungssensor aus, bleibt der Ladestand sichtbar."""
        app = self._app(variables, config, self._hass(leistung=zustand))
        assert app["text"] == "Speicher bei 57%"

    @pytest.mark.parametrize("soc,text", [("57.4", "57%"), ("57.6", "58%"), ("100", "100%"),
                                          ("0", "0%")])
    def test_ladestand_ganzzahlig(self, variables, config, soc, text):
        app = self._app(variables, config, self._hass(soc=soc), bat_power_sensor="")
        assert app["text"] == "Speicher bei " + text

    @pytest.mark.parametrize(
        "beschriftung,erwartet",
        [("Akku", "Akku 57% ^"), ("", "57% ^"), ("  Speicher  ", "Speicher 57% ^")],
    )
    def test_beschriftung_frei_waehlbar(self, variables, config, beschriftung, erwartet):
        app = self._app(variables, config, self._hass(), bat_label=beschriftung,
                        bat_up="^")
        assert app["text"] == erwartet

    def test_eigene_pfeilzeichen(self, variables, config):
        """Wer eine Schrift mit echten Pfeilen hat, kann sie eintragen."""
        laden = self._app(variables, config, self._hass(leistung="900"), bat_up="↑")
        entladen = self._app(variables, config, self._hass(leistung="-900"), bat_down="↓")
        assert laden["text"].endswith("↑") and entladen["text"].endswith("↓")

    def test_leeres_pfeilzeichen_hinterlaesst_kein_leerzeichen(self, variables, config):
        app = self._app(variables, config, self._hass(), bat_up="")
        assert app["text"] == "Speicher bei 57%"

    # --- Sichtbarkeit -----------------------------------------------
    @pytest.mark.parametrize("zustand", ["unknown", "unavailable"])
    def test_ohne_ladestand_ausgeblendet(self, variables, config, zustand):
        assert self._apps(variables, config, self._hass(soc=zustand)) == []

    def test_ohne_sensor_keine_app(self, variables, config):
        assert self._apps(variables, config, self._hass(), bat_sensor="") == []

    def test_leerer_speicher_bleibt_sichtbar(self, variables, config):
        """0 % ist eine Aussage, kein fehlender Wert."""
        app = self._app(variables, config, self._hass(soc="0", leistung="0"))
        assert app["text"] == "Speicher bei 0%"

    # --- Farbstufen -------------------------------------------------
    @pytest.mark.parametrize(
        "soc,stufe",
        [
            ("5", "bat_c_empty"),
            ("19.9", "bat_c_empty"),
            ("20", "bat_c_low"),
            ("39", "bat_c_low"),
            ("40", "bat_c_mid"),
            ("59", "bat_c_mid"),
            ("60", "bat_c_high"),
            ("79", "bat_c_high"),
            ("80", "bat_c_full"),
            ("100", "bat_c_full"),
        ],
    )
    def test_fuenf_farbstufen(self, variables, config, soc, stufe):
        app = self._app(variables, config, self._hass(soc=soc))
        assert app["color"] == config[stufe]

    def test_standardfarben_sind_verschieden(self, config):
        farben = [tuple(config[k]) for k in
                  ("bat_c_empty", "bat_c_low", "bat_c_mid", "bat_c_high", "bat_c_full")]
        assert len(set(farben)) == 5

    def test_standardschwellen_steigen(self, config):
        schwellen = [config[k] for k in ("bat_t_low", "bat_t_mid", "bat_t_high", "bat_t_full")]
        assert schwellen == sorted(schwellen) and len(set(schwellen)) == 4

    @pytest.mark.parametrize("schwelle", ["bat_t_low", "bat_t_mid", "bat_t_high", "bat_t_full"])
    def test_schwelle_gehoert_zur_oberen_stufe(self, variables, config, schwelle):
        """Genau auf der Schwelle gilt bereits die neue Farbe."""
        wert = config[schwelle]
        oben = self._app(variables, config, self._hass(soc=str(wert)))["color"]
        unten = self._app(variables, config, self._hass(soc=str(wert - 0.1)))["color"]
        assert oben != unten

    def test_eigene_schwellen_wirken(self, variables, config):
        app = self._app(variables, config, self._hass(soc="50"), bat_t_high=45)
        assert app["color"] == config["bat_c_high"], "50 % liegt über der neuen Schwelle 45"

    def test_farbe_haengt_nicht_an_der_leistung(self, variables, config):
        laden = self._app(variables, config, self._hass(soc="30", leistung="2000"))
        entladen = self._app(variables, config, self._hass(soc="30", leistung="-2000"))
        assert laden["color"] == entladen["color"] == config["bat_c_low"]

    def test_reihenfolge_nach_waermepumpe_vor_fenstern(self, build_apps):
        apps, _ = build_apps()
        texte = [a["text"] for a in apps]
        speicher = next(i for i, t in enumerate(texte) if t.startswith("Speicher"))
        assert texte[speicher - 1].startswith("WP")
        assert "Fenster" in texte[speicher + 1]


# ==========================================================================
# Temperatur: Farbskala und Einheit
# ==========================================================================
class TestTemperatur:
    def _app(self, variables, config, grad, **over):
        hass = FakeHass().set("sensor.aussentemperatur", str(grad), unit_of_measurement="°C")
        cfg = {**config, "show_time": False, "show_date": False, "pv_sensor": "",
               "hp_sensor": "", "window_sensors": [], "pv_w": 0, "hp_w": 0,
               "windows_open": 0, **over}
        return render(variables["apps"], hass, **cfg)[0]

    def test_einheit_klebt_am_wert(self, variables, config):
        assert self._app(variables, config, 7.34)["text"] == "7.3C"

    @pytest.mark.parametrize(
        "einheit,erwartet",
        [("C", "7.3C"), (" C", "7.3 C"), (" Grad", "7.3 Grad"), ("", "7.3"), ("°C", "7.3°C")],
    )
    def test_einheit_ist_frei_waehlbar(self, variables, config, einheit, erwartet):
        """Das Gradzeichen fehlt in den WLED-Schriften, deshalb einstellbar."""
        assert self._app(variables, config, 7.34, temp_unit=einheit)["text"] == erwartet

    def test_minusgrade(self, variables, config):
        assert self._app(variables, config, -8.2)["text"] == "-8.2C"

    @pytest.mark.parametrize(
        "grad,erwartet",
        [
            (-8, [140, 80, 255]),   # strenger Frost
            (-2, [60, 140, 255]),   # Frost
            (5, [0, 200, 255]),     # kühl
            (15, [0, 255, 120]),    # mild
            (22, [255, 200, 0]),    # warm
            (27, [255, 120, 0]),    # Sommertag ab 25
            (32, [255, 30, 0]),     # heißer Tag ab 30
            (38, [255, 0, 110]),    # Wüstentag ab 35
        ],
    )
    def test_standardskala(self, variables, config, grad, erwartet):
        assert self._app(variables, config, grad)["color"] == erwartet

    @pytest.mark.parametrize("grad", [-5, 0, 10, 20, 25, 30, 35])
    def test_schwelle_gehoert_zur_oberen_stufe(self, variables, config, grad):
        """Genau auf der Schwelle gilt bereits die neue Farbe."""
        oben = self._app(variables, config, grad)["color"]
        unten = self._app(variables, config, grad - 0.1)["color"]
        assert oben != unten

    def test_eigene_skala(self, variables, config):
        skala = [{"ab": -99, "farbe": [0, 0, 255]}, {"ab": 20, "farbe": [255, 0, 0]}]
        assert self._app(variables, config, 5, temp_scale=skala)["color"] == [0, 0, 255]
        assert self._app(variables, config, 25, temp_scale=skala)["color"] == [255, 0, 0]

    def test_einzige_stufe_ist_feste_farbe(self, variables, config):
        skala = [{"ab": -99, "farbe": [1, 2, 3]}]
        for grad in (-20, 0, 40):
            assert self._app(variables, config, grad, temp_scale=skala)["color"] == [1, 2, 3]


# ==========================================================================
# Einheit mit Leerzeichen, Gradzeichen ohne
# ==========================================================================
class TestEinheitenSchreibweise:
    def test_leistung_mit_leerzeichen(self, build_apps):
        apps, _ = build_apps()
        leistung = [a["text"] for a in apps if a["text"][:2] in ("PV", "WP")]
        assert leistung and all(" W" in t or " kW" in t for t in leistung)

    def test_temperatur_ohne_leerzeichen(self, build_apps):
        """Standard ist "7.3C" – die Einheit hängt ohne Lücke am Wert."""
        apps, _ = build_apps()
        grad = [a["text"] for a in apps if a["text"].endswith("C") and a["text"][0].isdigit()]
        assert grad and all(" C" not in t for t in grad)

    @pytest.mark.parametrize("watt,text", [(-2500, "-2.5 kW"), (-800, "-800 W")])
    def test_negative_werte_nutzen_den_betrag_fuer_die_einheit(
        self, variables, config, watt, text
    ):
        """Früher wurde -2500 W als "-2500 W" statt "-2.5 kW" angezeigt."""
        hass = FakeHass().set("sensor.pv", str(watt), unit_of_measurement="W")
        cfg = {**config, "show_time": False, "show_date": False, "temp_sensor": "",
               "hp_sensor": "", "window_sensors": [], "hp_w": 0, "windows_open": 0,
               "pv_only": False}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        assert render(variables["apps"], hass, **cfg)[0]["text"] == "PV " + text
