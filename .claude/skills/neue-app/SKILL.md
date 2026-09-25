---
name: neue-app
description: Neue App (Anzeige in der Rotation) zum WLED-Matrix-Blueprint hinzufügen, oder eine bestehende App um Eingaben erweitern. Listet jede Stelle in Blueprint, Tests, CI-Fixtures und Doku, die dabei angefasst werden muss.
---

# Neue App im Blueprint

Eine App berührt immer dieselben zehn Stellen. Fehlt eine, merkt man es oft
erst in der CI oder gar nicht. Arbeite die Liste der Reihe nach ab. Vorlage
für Aufbau und Stil ist die App, die der neuen am nächsten kommt, meist die
Wärmepumpe (`hp_*`) oder der PV-Speicher (`bat_*`).

## 1. Test zuerst

In `tests/test_vorlagen.py` eine Klasse `Test<App>` nach dem Muster von
`TestSpeicher`: eigene `_hass()`, `_apps()` mit allen anderen Apps abgeschaltet.
Mindestens abdecken:

- Text und Formatierung, auch Randwerte (0, negativ, sehr groß)
- jede Farbstufe, Schwellen inklusiv (`test_schwelle_gehoert_zur_oberen_stufe`)
- `unknown` / `unavailable` blendet aus oder fällt sauber zurück
- W/kW-Erkennung und Vorzeichenumkehr, falls es eine Leistung gibt
- Position in der Rotation

Testen, dass die Tests fehlschlagen, bevor der Blueprint geändert ist.

## 2. Blueprint `blueprints/automation/wled_matrix/wled_matrix_display.yaml`

1. **Abschnitt** unter `blueprint.input`: `app_<name>`, Name endet auf
   `(optional)`, `icon: mdi:...`, `collapsed: true`. Position = Position in
   der Rotation.
2. **Eingaben**: jede mit `name`, `selector` und `default`. Nur `wled_light`
   darf ohne Standardwert sein.
   - Entität, die in einem **Trigger** landet: `default: []`, nie `""`.
   - Schrift: Feld `<name>_font`, Optionen exakt wie bei den anderen Apps,
     Standard `""` („wie eingestellt“).
   - Zeichen, die auf der Matrix erscheinen: Standard nur ASCII 32–126. Die
     eingebauten WLED-Schriften kennen nichts anderes (0.14/0.15 lassen es
     weg, 16 zeigt `?`). Beschreibung soll darauf hinweisen.
   - Stolperfallen (Vorzeichen, Schwellen, unter denen die App verschwindet)
     in der Beschreibung erklären, mit dem Weg über Entwicklerwerkzeuge →
     Zustände.
3. **`variables`**: jede Eingabe per `!input` einbinden, Schrift bei den
   anderen `*_font`. Umrechnungen (W/kW, Vorzeichen) als eigene Variable wie
   `hp_w` / `bat_w`, damit sie einzeln testbar sind.
4. **`apps`-Vorlage**: Block an der passenden Stelle. Kommentar in `{# #}`
   ohne Umlaute, wie die übrigen. `font` nur setzen, wenn gewählt:
   `**({'font': x_font} if x_font else {})`.
5. **Beschreibung** oben im Blueprint (Aufzählung unter „APPS“).

## 3. Tests nachziehen

- `tests/conftest.py`: Sensoren im Standardhaushalt (`hass`), Werte in
  `config` (Standardwerte über `input_default()`, nicht abschreiben), neue
  Umrechnungsvariable in `build_apps`.
- `tests/test_struktur.py`: `SEKTIONEN`, Parameterliste von
  `test_schriftauswahl_pro_app`, ggf. `test_stolperfallen_sind_erklaert`, und die
  Feldzahl im Docstring von `test_nur_pflichtabschnitte_sind_aufgeklappt`.
- `tests/test_vorlagen.py`: `test_alle_apps_in_richtiger_reihenfolge`,
  `test_nur_uhr_wenn_nichts_konfiguriert`, Parameter in `TestSchriftProApp`.
- `tests/test_befehle.py`: typischen Text in `test_texte_bleiben_unveraendert`.

## 4. CI-Fixtures

- `tests/fixtures/automations.yaml`: jede neue Eingabe in `vollstaendig`
  belegen (`test_fixture_deckt_alle_eingaben_ab` prüft das).
- `tests/fixtures/configuration.yaml`: Template-Sensoren für die dort
  referenzierten Entitäten.

## 5. Gegenprobe

Den Blueprint an den wichtigen Stellen absichtlich kaputt machen (Schwelle
exklusiv, Umkehr wirkungslos, Prüfung auf `unavailable` entfernt …) und
prüfen, dass `uv run pytest` anschlägt. Danach die Datei wiederherstellen und
mit `git diff` kontrollieren. Erkannte Fehler in die Tabelle in
`docs/entwicklung.md` eintragen und die Zahl im Satz davor anpassen.

## 6. Doku

- `README.md`: Zeile in der App-Tabelle.
- `docs/anleitung.md`: Tabelle oben, Entitäten-Checkliste in Teil 1, Punkt
  in Teil 5, Anzahl der Abschnitte in Teil 5, Zeilen in der Fehlersuche.

## 7. Abschluss

```bash
uv run pytest && uv run yamllint --strict .
```

Nicht committen, der Nutzer testet erst am echten Home Assistant (Skill
`ha-testen`). Commit-Vorschlag nennen: `feat: <App> zeigt …`.
