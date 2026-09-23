"""Die JSON-Befehle, die an WLED gehen.

Die Vorlagen werden aus den Zweigen des Blueprints gelesen, nicht nachgebaut.
So schlagen die Tests an, sobald sich der tatsächlich gesendete Befehl ändert.
"""

from __future__ import annotations

import pytest

from conftest import render

MAX_TEXT = 64


def _payload(branch) -> str:
    """Die erste REST-Nutzlast eines Zweigs."""
    for schritt in branch["sequence"]:
        if isinstance(schritt, dict) and schritt.get("action") == "rest_command.wled_matrix_json":
            return schritt["data"]["data"]
    raise AssertionError("Zweig sendet keinen REST-Befehl")


@pytest.fixture
def rotation_payload(branches):
    return _payload(branches["App-Rotation"])


@pytest.fixture
def nachricht_payload(branches):
    return _payload(branches["Benachrichtigung anzeigen"])


@pytest.fixture
def defaults(config):
    return {k: config[k] for k in ("fonts", "def_font", "def_speed", "def_bri", "def_y")}


# ==========================================================================
# Gemeinsame Form
# ==========================================================================
class TestGrundform:
    def test_rotation_baut_gueltigen_befehl(self, rotation_payload, hass, defaults):
        out = render(
            rotation_payload, hass, item={"text": "#TIME", "color": [0, 255, 150]}, fx_id=122, **defaults
        )
        assert out["on"] is True
        assert len(out["seg"]) == 1
        seg = out["seg"][0]
        assert seg["id"] == 0
        assert seg["fx"] == 122
        assert seg["n"] == "#TIME"
        assert seg["col"] == [[0, 255, 150], [0, 0, 0], [0, 0, 255]]

    def test_nachricht_baut_gueltigen_befehl(self, nachricht_payload, hass, defaults):
        out = render(
            nachricht_payload,
            hass,
            ev={},
            msg="Waesche fertig",
            notify_color=[255, 255, 255],
            fx_id=122,
            **defaults,
        )
        assert out["seg"][0]["n"] == "Waesche fertig"
        assert out["seg"][0]["col"][0] == [255, 255, 255]

    @pytest.mark.parametrize("schluessel", ["on", "bri", "seg"])
    def test_pflichtschluessel(self, rotation_payload, hass, defaults, schluessel):
        out = render(rotation_payload, hass, item={"text": "x"}, fx_id=122, **defaults)
        assert schluessel in out

    @pytest.mark.parametrize(
        "feld", ["id", "fx", "n", "sx", "ix", "c1", "c2", "o1", "o2", "o3", "col"]
    )
    def test_segmentfelder(self, rotation_payload, hass, defaults, feld):
        out = render(rotation_payload, hass, item={"text": "x"}, fx_id=122, **defaults)
        assert feld in out["seg"][0]


# ==========================================================================
# Text
# ==========================================================================
class TestText:
    def test_wird_auf_64_zeichen_gekuerzt(self, rotation_payload, hass, defaults):
        out = render(rotation_payload, hass, item={"text": "x" * 200}, fx_id=122, **defaults)
        assert len(out["seg"][0]["n"]) == MAX_TEXT

    def test_nachricht_wird_ebenfalls_gekuerzt(self, nachricht_payload, hass, defaults):
        out = render(
            nachricht_payload, hass, ev={}, msg="y" * 200, notify_color=[255, 255, 255],
            fx_id=122, **defaults,
        )
        assert len(out["seg"][0]["n"]) == MAX_TEXT

    def test_nachricht_wird_getrimmt(self, nachricht_payload, hass, defaults):
        out = render(
            nachricht_payload, hass, ev={}, msg="  Hallo  ", notify_color=[255, 255, 255],
            fx_id=122, **defaults,
        )
        assert out["seg"][0]["n"] == "Hallo"

    @pytest.mark.parametrize("text", ["#TIME", "#DATE", "PV 3.2kW", "2 Fenster offen"])
    def test_texte_bleiben_unveraendert(self, rotation_payload, hass, defaults, text):
        out = render(rotation_payload, hass, item={"text": text}, fx_id=122, **defaults)
        assert out["seg"][0]["n"] == text


# ==========================================================================
# Standardwerte und Überschreibungen
# ==========================================================================
class TestWerte:
    def test_standardwerte_greifen(self, rotation_payload, hass, defaults):
        out = render(rotation_payload, hass, item={"text": "x"}, fx_id=122, **defaults)
        seg = out["seg"][0]
        assert (out["bri"], seg["sx"], seg["ix"], seg["c2"]) == (128, 128, 128, 128)

    def test_app_ueberschreibt_standard(self, rotation_payload, hass, defaults):
        item = {"text": "x", "brightness": 200, "speed": 30, "y_offset": 0, "font": "4x6"}
        out = render(rotation_payload, hass, item=item, fx_id=122, **defaults)
        seg = out["seg"][0]
        assert (out["bri"], seg["sx"], seg["ix"], seg["c2"]) == (200, 30, 0, 0)

    @pytest.mark.parametrize("font,c2", [("4x6", 0), ("5x8", 64), ("6x8", 128)])
    def test_schriftzuordnung(self, rotation_payload, hass, defaults, font, c2):
        out = render(rotation_payload, hass, item={"text": "x", "font": font}, fx_id=122, **defaults)
        assert out["seg"][0]["c2"] == c2

    def test_event_ueberschreibt_standard(self, nachricht_payload, hass, defaults):
        ev = {"color": [255, 0, 0], "speed": 230, "font": "5x8", "brightness": 255}
        out = render(
            nachricht_payload, hass, ev=ev, msg="Alarm", notify_color=[255, 255, 255],
            fx_id=122, **defaults,
        )
        seg = out["seg"][0]
        assert (seg["col"][0], seg["sx"], seg["c2"], out["bri"]) == ([255, 0, 0], 230, 64, 255)

    def test_farbverlauf(self, rotation_payload, hass, defaults):
        item = {"text": "x", "gradient": True, "color": [255, 200, 0], "color2": [255, 60, 0]}
        out = render(rotation_payload, hass, item=item, fx_id=122, **defaults)
        seg = out["seg"][0]
        assert seg["o1"] is True
        assert seg["col"][0] == [255, 200, 0]
        assert seg["col"][2] == [255, 60, 0]

    def test_overlay_ist_aus(self, rotation_payload, hass, defaults):
        """Sonst bliebe der vorherige Text stehen."""
        out = render(rotation_payload, hass, item={"text": "x"}, fx_id=122, **defaults)
        assert out["seg"][0]["o2"] is False

    def test_richtung_umkehrbar(self, rotation_payload, hass, defaults):
        out = render(rotation_payload, hass, item={"text": "x", "reverse": True}, fx_id=122, **defaults)
        assert out["seg"][0]["o3"] is True


# ==========================================================================
# Wertebereiche, die WLED akzeptiert
# ==========================================================================
class TestGrenzen:
    @pytest.mark.parametrize(
        "item",
        [
            {"text": "x"},
            {"text": "x", "brightness": 1},
            {"text": "x", "brightness": 255},
            {"text": "x", "speed": 0},
            {"text": "x", "speed": 255},
            {"text": "x", "trail": 255},
            {"text": "x", "y_offset": 0},
        ],
    )
    def test_werte_bleiben_im_erlaubten_bereich(self, rotation_payload, hass, defaults, item):
        out = render(rotation_payload, hass, item=item, fx_id=122, **defaults)
        seg = out["seg"][0]
        assert 1 <= out["bri"] <= 255
        for feld in ("sx", "ix", "c1", "c2"):
            assert 0 <= seg[feld] <= 255
        for kanal in seg["col"]:
            assert len(kanal) == 3 and all(0 <= c <= 255 for c in kanal)

    def test_alles_ist_json_serialisierbar(self, rotation_payload, hass, defaults):
        import json

        out = render(rotation_payload, hass, item={"text": "#TIME"}, fx_id=122, **defaults)
        assert json.loads(json.dumps(out)) == out


# ==========================================================================
# Effekt-ID: 0 bedeutet "Effekt nicht umschalten"
# ==========================================================================
class TestEffektUmschalten:
    def test_id_wird_gesetzt(self, rotation_payload, hass, defaults):
        out = render(rotation_payload, hass, item={"text": "x"}, fx_id=122, **defaults)
        assert out["seg"][0]["fx"] == 122

    @pytest.mark.parametrize("payload", ["rotation_payload", "nachricht_payload"])
    def test_null_laesst_fx_weg(self, request, hass, defaults, payload):
        """Bei 0 darf kein "fx" im Befehl stehen.

        Sonst würde WLED auf Effekt 0 (Solid) umschalten und der Lauftext
        wäre weg. Wer 0 einträgt, hat den Effekt in WLED selbst gesetzt.
        """
        vorlage = request.getfixturevalue(payload)
        extra = ({"item": {"text": "x"}} if payload == "rotation_payload"
                 else {"ev": {}, "msg": "x", "notify_color": [255, 255, 255]})
        out = render(vorlage, hass, fx_id=0, **extra, **defaults)
        assert "fx" not in out["seg"][0]
        # Der Rest muss unverändert mitgehen
        assert out["seg"][0]["n"] == "x"
        assert out["seg"][0]["id"] == 0
