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
            show_date=False, temp_sensor="", pv_sensor="", hp_sensor="", window_sensors=[]
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
class TestRotation:
    @pytest.mark.parametrize("pattern,sekunden", [("/10", 10), ("/15", 15), ("/30", 30), ("0", 60)])
    def test_intervall_umrechnung(self, hass, pattern, sekunden):
        vorlage = "{{ 60 if pattern == '0' else pattern[1:] | int }}"
        assert render(vorlage, hass, pattern=pattern) == sekunden

    def test_reihenfolge_ist_stabil_und_vollstaendig(self, build_apps, hass):
        apps, _ = build_apps()
        vorlage = "{{ apps[ ((ts | int) // (secs | int)) % (apps | count) ].text }}"
        gesehen = [
            render(vorlage, hass, apps=apps, ts=1758470400 + i * 15, secs=15)
            for i in range(len(apps))
        ]
        assert gesehen == [a["text"] for a in apps]

    def test_rotation_laeuft_rund(self, build_apps, hass):
        """Nach einem vollen Durchlauf beginnt es wieder bei der ersten App."""
        apps, _ = build_apps()
        vorlage = "{{ ((ts | int) // 15) % (apps | count) }}"
        start = render(vorlage, hass, apps=apps, ts=1758470400)
        rum = render(vorlage, hass, apps=apps, ts=1758470400 + 15 * len(apps))
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
