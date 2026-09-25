"""Gemeinsame Test-Hilfen.

Kernidee: Die Tests rendern die Jinja-Vorlagen **direkt aus der Blueprint-Datei**
statt Kopien davon. Ändert jemand den Blueprint, ändern sich die Tests mit.

Dafür wird die Template-Umgebung von Home Assistant so weit nachgebaut, wie der
Blueprint sie nutzt:

* ``!input`` wird beim YAML-Laden als Platzhalter aufgelöst
* die HA-Funktionen ``states``, ``state_attr``, ``is_state``, ``device_id``
  und ``device_attr`` werden aus einer Zustandstabelle bedient
* die HA-Filter ``bool``, ``regex_replace`` und der Test ``is_state``
* HA gibt Vorlagen als native Python-Typen zurück (Liste, Dict, Zahl, bool),
  nicht als Zeichenkette – das macht ``native()`` nach.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from jinja2 import Environment, StrictUndefined

REPO = Path(__file__).resolve().parent.parent
BLUEPRINT = REPO / "blueprints" / "automation" / "wled_matrix" / "wled_matrix_display.yaml"


# --------------------------------------------------------------------------
# YAML mit !input laden
# --------------------------------------------------------------------------
class BlueprintLoader(yaml.SafeLoader):
    """SafeLoader, der ``!input xyz`` als ``('INPUT', 'xyz')`` einliest."""


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: ("INPUT", loader.construct_scalar(node))
)


def load_blueprint(path: Path = BLUEPRINT) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=BlueprintLoader)


def input_names(path: Path = BLUEPRINT) -> set[str]:
    """Alle per ``!input`` referenzierten Namen aus dem Dateitext."""
    return set(re.findall(r"!input\s+(\w+)", path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------
# Zustandstabelle (das "Home Assistant" der Tests)
# --------------------------------------------------------------------------
class FakeHass:
    """Minimale Zustandstabelle: Entity -> (state, attribute)."""

    def __init__(self, states: dict[str, tuple[str, dict]] | None = None):
        self.states: dict[str, tuple[str, dict]] = states or {}

    def set(self, entity: str, state: str, **attrs: Any) -> "FakeHass":
        self.states[entity] = (state, attrs)
        return self

    # --- HA-Funktionen -------------------------------------------------
    def fn_states(self, entity: str) -> str:
        return self.states.get(entity, ("unknown", {}))[0]

    def fn_state_attr(self, entity: str, attr: str) -> Any:
        return self.states.get(entity, ("unknown", {}))[1].get(attr)

    def fn_is_state(self, entity: str, value: str) -> bool:
        return self.fn_states(entity) == value

    def fn_device_id(self, entity: str) -> str:
        return f"dev_{entity}"

    def fn_device_attr(self, device: str, attr: str) -> Any:
        entity = device.removeprefix("dev_")
        return self.states.get(entity, ("unknown", {}))[1].get(attr)


# --------------------------------------------------------------------------
# Jinja-Umgebung wie in Home Assistant
# --------------------------------------------------------------------------
def _filter_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "on", "1")
    if value is None:
        return False
    return bool(value)


def _filter_regex_replace(value: Any, find: str = "", replace: str = "", ignorecase: bool = False):
    flags = re.IGNORECASE if ignorecase else 0
    return re.sub(find, replace, str(value), flags=flags)


def make_env(hass: FakeHass) -> Environment:
    env = Environment(undefined=StrictUndefined)
    env.filters["bool"] = _filter_bool
    env.filters["regex_replace"] = _filter_regex_replace
    # HA erlaubt "liste | select('is_state', 'on')"
    env.filters["select"] = lambda seq, test, *args: [
        x for x in seq if (hass.fn_is_state(x, *args) if test == "is_state" else bool(x))
    ]
    env.tests["is_state"] = hass.fn_is_state
    env.globals.update(
        states=hass.fn_states,
        state_attr=hass.fn_state_attr,
        is_state=hass.fn_is_state,
        device_id=hass.fn_device_id,
        device_attr=hass.fn_device_attr,
    )
    return env


def native(text: str) -> Any:
    """Wie HA: Ergebnis in einen Python-Typ umwandeln, sonst getrimmter Text."""
    stripped = text.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError):
        return stripped


def render(template: str, hass: FakeHass, **context: Any) -> Any:
    return native(make_env(hass).from_string(template).render(**context))


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def blueprint() -> dict:
    return load_blueprint()


@pytest.fixture(scope="session")
def variables(blueprint: dict) -> dict:
    return blueprint["variables"]


@pytest.fixture(scope="session")
def branches(blueprint: dict) -> dict:
    """Die Zweige aus ``choose``, nach ihrem alias benannt."""
    return {b["alias"]: b for b in blueprint["actions"][0]["choose"]}


@pytest.fixture
def hass() -> FakeHass:
    """Standardhaushalt: PV in kW, Wärmepumpe in W, Speicher lädt, zwei von drei Fenstern offen."""
    effects = ["Solid"] + ["RSVD"] * 120 + ["Blends", "Scrolling Text", "Image Effect"]
    return (
        FakeHass()
        .set("light.matrix", "on", effect_list=effects, configuration_url="http://192.168.1.50/")
        .set("sensor.aussentemperatur", "7.34", unit_of_measurement="°C")
        .set("sensor.pv", "3.2", unit_of_measurement="kW")
        .set("sensor.wp", "820", unit_of_measurement="W")
        .set("sensor.speicher", "57.4", unit_of_measurement="%")
        .set("sensor.speicher_leistung", "1.2", unit_of_measurement="kW")
        .set("binary_sensor.fenster_1", "on")
        .set("binary_sensor.fenster_2", "off")
        .set("binary_sensor.fenster_3", "on")
        .set("binary_sensor.praesenz", "on")
    )


def find_input(blueprint: dict, name: str) -> dict:
    """Eine Eingabe suchen, egal in welchem Abschnitt sie liegt.

    Die Abschnitte sind nur zum Aufräumen der Oberfläche da. Tests sollen nicht
    umgeschrieben werden müssen, wenn ein Feld in einen anderen Abschnitt wandert.
    """
    for sektion in blueprint["blueprint"]["input"].values():
        if name in sektion["input"]:
            return sektion["input"][name]
    raise KeyError(f"Eingabe nicht gefunden: {name}")


def all_inputs(blueprint: dict) -> dict:
    """Alle Eingaben aus allen Abschnitten, flach."""
    return {
        name: feld
        for sektion in blueprint["blueprint"]["input"].values()
        for name, feld in sektion["input"].items()
    }


def input_default(blueprint: dict, name: str) -> Any:
    """Standardwert einer Eingabe – damit Tests keine zweite Kopie pflegen."""
    return find_input(blueprint, name)["default"]


@pytest.fixture
def config(blueprint, variables) -> dict:
    """Vollständig ausgefüllte Blueprint-Eingaben.

    ``fonts`` wird bewusst aus dem Blueprint gelesen und nicht hier noch einmal
    hingeschrieben – sonst würde eine falsche Zuordnung im Blueprint von einer
    zweiten, richtigen Kopie im Test verdeckt.
    """
    return {
        "light_entity": "light.matrix",
        "host_input": "",
        "fx_input": 0,
        "fx_name": "Scrolling Text",
        "show_time": True,
        "time_color": [0, 255, 150],
        "show_date": True,
        "date_color": [255, 255, 255],
        "temp_sensor": "sensor.aussentemperatur",
        "temp_scale": input_default(blueprint, "temp_scale"),
        "temp_unit": input_default(blueprint, "temp_unit"),
        "pv_sensor": "sensor.pv",
        "pv_only": True,
        "pv_c_low": [255, 60, 0],
        "pv_c_mid": [255, 200, 0],
        "pv_c_high": [0, 255, 0],
        "pv_t_mid": 500,
        "pv_t_high": 2000,
        "hp_sensor": "sensor.wp",
        "hp_only": True,
        "hp_invert": False,
        "hp_t_idle": 100,
        "hp_t_mid": 800,
        "hp_t_high": 2000,
        "hp_c_idle": [60, 120, 200],
        "hp_c_low": [0, 255, 80],
        "hp_c_mid": [255, 200, 0],
        "hp_c_high": [255, 60, 0],
        # Speicher: Schwellen, Farben, Pfeile und Beschriftung kommen aus den
        # Standardwerten des Blueprints, damit die Tests genau die ausgelieferte
        # Einstellung prüfen.
        "bat_sensor": "sensor.speicher",
        "bat_power_sensor": "sensor.speicher_leistung",
        "bat_invert": False,
        "bat_label": input_default(blueprint, "bat_label"),
        "bat_up": input_default(blueprint, "bat_arrow_up"),
        "bat_down": input_default(blueprint, "bat_arrow_down"),
        "bat_t_idle": input_default(blueprint, "bat_threshold_idle"),
        "bat_t_low": input_default(blueprint, "bat_threshold_low"),
        "bat_t_mid": input_default(blueprint, "bat_threshold_mid"),
        "bat_t_high": input_default(blueprint, "bat_threshold_high"),
        "bat_t_full": input_default(blueprint, "bat_threshold_full"),
        "bat_c_empty": input_default(blueprint, "bat_color_empty"),
        "bat_c_low": input_default(blueprint, "bat_color_low"),
        "bat_c_mid": input_default(blueprint, "bat_color_mid"),
        "bat_c_high": input_default(blueprint, "bat_color_high"),
        "bat_c_full": input_default(blueprint, "bat_color_full"),
        "window_sensors": [
            "binary_sensor.fenster_1",
            "binary_sensor.fenster_2",
            "binary_sensor.fenster_3",
        ],
        "window_only": True,
        "window_color": [255, 80, 80],
        "custom_apps": [],
        # "" = wie eingestellt, also Schrift aus Abschnitt 3
        "time_font": "",
        "date_font": "",
        "temp_font": "",
        "pv_font": "",
        "hp_font": "",
        "bat_font": "",
        "window_font": "",
        "def_font": "6x8",
        "def_speed": 128,
        "def_bri": 128,
        "def_y": 128,
        "fonts": variables["fonts"],
    }


@pytest.fixture
def build_apps(variables, hass, config):
    """Baut die App-Liste mit der echten Vorlage aus dem Blueprint."""

    def _build(**overrides):
        cfg = {**config, **overrides}
        cfg["pv_w"] = render(variables["pv_w"], hass, **cfg)
        cfg["hp_w"] = render(variables["hp_w"], hass, **cfg)
        cfg["bat_w"] = render(variables["bat_w"], hass, **cfg)
        cfg["windows_open"] = render(variables["windows_open"], hass, **cfg)
        return render(variables["apps"], hass, **cfg), cfg

    return _build
