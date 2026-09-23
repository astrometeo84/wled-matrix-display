# WLED Matrix Display für Home Assistant

Ein Blueprint, der aus einer WLED-Matrix eine Info-Anzeige macht — Apps im Wechsel, Benachrichtigungen dazwischen, und die Matrix schaltet sich ab, wenn niemand im Raum ist. Vergleichbar mit der Ulanzi/Awtrix-Uhr, aber für beliebige WLED-Matrizen.

[![Validierung](https://github.com/astrometeo84/wled-matrix-display/actions/workflows/validate.yml/badge.svg)](https://github.com/astrometeo84/wled-matrix-display/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/astrometeo84/wled-matrix-display)](https://github.com/astrometeo84/wled-matrix-display/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[![In Home Assistant öffnen](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fastrometeo84%2Fwled-matrix-display%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fwled_matrix%2Fwled_matrix_display.yaml)

---

## Funktionen

**Apps im Wechsel** — die Matrix zeigt der Reihe nach an, was gerade wichtig ist:

| App | Voraussetzung | Beispiel |
|---|---|---|
| Uhrzeit | — | `#TIME` |
| Datum | — | `#DATE` |
| Außentemperatur | Sensor | `7.3C` |
| PV-Leistung | Sensor | `PV 3.2kW`, Farbe nach Höhe |
| Wärmepumpe | Sensor | `WP 820W` |
| Offene Fenster | Fensterkontakte | `2 Fenster offen` |
| Eigene Apps | — | frei als YAML-Liste |

Jede App blendet sich selbst aus, wenn sie nichts zu melden hat: kein PV-Ertrag nachts, Wärmepumpe steht, alle Fenster zu. Die Einheit der Leistungssensoren (W oder kW) wird automatisch erkannt. Die Effekt-ID des Lauftext-Effekts ist fest auf 122 voreingestellt und lässt sich im Blueprint ändern, siehe [Anleitung, Teil 2](docs/anleitung.md#teil-2--effekt-id-herausfinden).

**Benachrichtigungen** unterbrechen die Rotation und danach läuft sie weiter. Ausgelöst über ein Event aus beliebigen Automationen oder über ein Texteingabefeld auf dem Dashboard.

**Anwesenheit und Stromsparen**: Anzeige aus bei leerem Raum, nach längerer Abwesenheit optional Stromtrennung über eine schaltbare Steckdose, bei Rückkehr automatisch wieder an.

## Installation

1. **REST-Command** in die `configuration.yaml` eintragen:

   ```yaml
   rest_command:
     wled_matrix_json:
       url: "http://{{ host }}/json/state"
       method: POST
       content_type: "application/json"
       payload: "{{ data if data is string else data | to_json }}"
   ```

2. Home Assistant neu starten.
3. Blueprint über den Knopf oben importieren.
4. Automation daraus erstellen und die Matrix auswählen.

Die ausführliche Schritt-für-Schritt-Anleitung mit Checkliste steht in **[docs/anleitung.md](docs/anleitung.md)**.

## Benachrichtigung auslösen

```yaml
- action: event.fire
  data:
    event_type: wled_matrix_notify
    event_data:
      text: "Waesche ist fertig!"
      color: [0, 255, 0]
      duration: 30
```

Weitere Felder: `gradient`, `color2`, `speed`, `font`, `brightness`, `y_offset`, `reverse`, `trail`.

## Voraussetzungen

- Home Assistant **2024.6** oder neuer (wegen der Eingabe-Abschnitte im Blueprint)
- WLED **0.14** oder neuer mit 2D-Matrix-Konfiguration und dem Effekt „Scrolling Text“
- Die Matrix über die offizielle WLED-Integration eingebunden

Entwickelt und getestet mit einer 64×8-Matrix. Andere Größen funktionieren, bei 8 Pixeln Höhe passen die Schriften `5x8` und `6x8` am besten.

## Mitmachen

Fehler und Wünsche gern als Issue.

Für Änderungen: `main` ist geschützt, es läuft alles über Pull Requests mit [Conventional Commits](https://www.conventionalcommits.org/de/). Version und CHANGELOG entstehen daraus automatisch. Der Ablauf steht in **[CONTRIBUTING.md](CONTRIBUTING.md)**, die technischen Hintergründe in **[docs/entwicklung.md](docs/entwicklung.md)**.

Tests laufen mit [uv](https://docs.astral.sh/uv/): `uv run pytest`.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
