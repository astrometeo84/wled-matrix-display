# Entwicklung

## Tests lokal ausführen

Das Projekt benutzt [uv](https://docs.astral.sh/uv/) für Python-Umgebung und
Werkzeuge. Einmalig installieren:

```bash
# Linux, macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows, PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Danach überall gleich, ohne virtuelle Umgebung von Hand anzulegen oder zu
aktivieren:

```bash
uv run pytest              # alle Tests
uv run pytest -v           # mit Namen
uv run pytest -k Schrift   # nur passende Tests
uv run yamllint --strict . # YAML-Stil
```

`uv run` legt die Umgebung beim ersten Aufruf selbst an, installiert was fehlt
und führt den Befehl darin aus. Unter Windows entfällt damit das Aktivieren
über `Activate.ps1` samt der Execution-Policy-Hürde.

### Abhängigkeiten ändern

Sie stehen in der `pyproject.toml` unter `[dependency-groups] dev`. Nach einer
Änderung die Sperrdatei neu erzeugen und mit einchecken:

```bash
uv lock
```

`uv.lock` hält die exakten Versionen fest, mit denen auch die CI arbeitet. Die
Workflows laufen mit `--locked` und brechen ab, wenn Sperrdatei und
`pyproject.toml` auseinanderlaufen. So kann ein frisch veröffentlichtes pytest
die CI nicht unbemerkt rot färben.

Aktualisieren geht mit `uv lock --upgrade`.

## Wie die Tests aufgebaut sind

Die Tests lesen die Jinja-Vorlagen **direkt aus der Blueprint-Datei** statt Kopien davon zu prüfen. Änderst du den Blueprint, prüfen die Tests automatisch die neue Fassung. Dafür baut `tests/conftest.py` die Template-Umgebung von Home Assistant so weit nach, wie der Blueprint sie braucht: die Funktionen `states`, `state_attr`, `is_state`, `device_attr`, die Filter `bool` und `regex_replace`, und die Umwandlung des Ergebnisses in echte Python-Typen.

| Datei | Prüft |
|---|---|
| `tests/test_struktur.py` | Aufbau: Abschnitte, Eingaben, Selektoren, Trigger, Zweige |
| `tests/test_vorlagen.py` | Logik: IP-Erkennung, Effekt-ID, Einheiten, App-Liste, Rotation |
| `tests/test_befehle.py` | Die JSON-Befehle, die tatsächlich an WLED gehen |

Ein paar Tests sind bewusst streng, weil sie Fehler abfangen, die im Betrieb schwer zu finden sind:

- **Jede Eingabe wird benutzt.** Eine referenzierte, aber nicht definierte Eingabe lässt Home Assistant den Blueprint gar nicht erst laden.
- **Nur die Matrix ist Pflicht.** Alle anderen Felder brauchen einen Standardwert, sonst blockiert die Einrichtung.
- **Der Stromschalter darf keine Lampe sein.** Sonst könnte man versehentlich die Matrix selbst als ihren eigenen Stromschalter wählen.
- **Die Rotation schaltet die Matrix nie ein.** Eine von Hand ausgeschaltete Matrix soll ausgeschaltet bleiben.
- **Die Schriftwerte sind festgenagelt.** `0 / 64 / 128` sind durch WLED vorgegeben; verschieben sie sich, zeigt die Matrix eine andere Schrift als ausgewählt.

### Doppelte Wahrheiten vermeiden

Werte, die im Blueprint stehen, werden in den Tests **nicht noch einmal hingeschrieben**, sondern von dort gelesen. Sonst verdeckt eine richtige Kopie im Test einen Fehler im Blueprint. Die Schrifttabelle ist das Beispiel dafür: Sie kommt über `variables["fonts"]` aus der Datei. Nur an genau einer Stelle steht die erwartete Zuordnung ausgeschrieben, nämlich in `test_schriftwerte_entsprechen_wled`, und die dokumentiert eine Vorgabe von WLED.

### Taugen die Tests etwas?

Prüfen lässt sich das, indem man den Blueprint absichtlich kaputt macht und schaut, ob die Tests anschlagen. Diese siebzehn Änderungen werden erkannt:

| Eingebauter Fehler | Wird erkannt |
|---|---|
| Textkürzung auf 64 Zeichen entfernt | ✅ |
| Overlay eingeschaltet (alter Text bliebe stehen) | ✅ |
| Schrifttabelle verfälscht | ✅ |
| PV-Farbschwelle verschoben | ✅ |
| Prüfung auf `unavailable` entfernt | ✅ |
| kW-Erkennung kaputt | ✅ |
| Lampe als Stromschalter erlaubt | ✅ |
| Leerer Text statt `[]` bei einer Trigger-Entität | ✅ |
| `fx` wird trotz Effekt-ID 0 mitgesendet | ✅ |
| Eine App legt ungefragt eine Schrift fest | ✅ |
| Eingabe umbenannt, CI-Fixture nicht nachgezogen | ✅ |
| Vorzeichenumkehr der Wärmepumpe wirkungslos | ✅ |
| Gradzeichen entfernt | ✅ |
| Leerzeichen vor `W` oder `kW` entfernt | ✅ |
| Betrag bei der Einheitenwahl entfernt | ✅ |
| Schwelle der Farbskala exklusiv statt inklusiv | ✅ |
| Bereitschafts-Schwelle der Wärmepumpe ignoriert | ✅ |

Viele davon stehen für Fehler, die im Betrieb tatsächlich aufgetreten sind.
Jeder davon hat erst einen Test bekommen, nachdem er aufgefallen war.

Kommt eine Funktion dazu, lohnt sich derselbe Handgriff: erst den Test schreiben, dann prüfen, ob er ohne die Funktion wirklich fehlschlägt.

## GitHub Actions

### `validate.yml` — bei jedem Push und Pull Request

| Job | Inhalt |
|---|---|
| `yamllint` | YAML-Stil |
| `tests` | pytest auf Python 3.11, 3.12 und 3.13 |
| `home-assistant` | Home Assistant lädt den Blueprint wirklich |

Der dritte Job ist der aussagekräftigste. Er baut aus `tests/fixtures/` eine vollständige Home-Assistant-Konfiguration, legt zwei Automationen aus dem Blueprint an — eine nur mit Pflichtfeldern, eine mit allen Eingaben belegt — und lässt Home Assistant die Konfiguration prüfen. Damit fallen Fehler auf, die eine reine Textprüfung nicht sieht, etwa ein Selektor, der einen Wert nicht annimmt.

Schlägt dieser Job wegen einer Änderung in Home Assistant fehl und du willst ihn nicht mehr, lösche den Block `home-assistant:` aus der Datei. Die anderen beiden Jobs laufen unabhängig davon weiter.

### `release.yml` — bei einem Tag `v*`

Der Ablauf:

1. Tests laufen. Sind sie rot, gibt es kein Release.
2. `scripts/check_version.py` vergleicht den Tag mit der Zeile `# Version:` im Kopf des Blueprints. Weichen sie ab, bricht der Lauf ab.
3. Die Commit-Titel seit dem letzten Tag werden zu Release-Notizen zusammengefasst.
4. Das Release wird angelegt, der Blueprint hängt als Datei daran.

Ein Tag mit Bindestrich, etwa `v1.1.0-beta1`, wird automatisch als Vorabversion markiert.

## Ein Release veröffentlichen

```bash
# 1. Version an BEIDEN Stellen anheben
#    blueprints/automation/wled_matrix/wled_matrix_display.yaml  ->  # Version: 1.1.0
#    pyproject.toml                                              ->  version = "1.1.0"
#    Ein Test prüft, dass beide übereinstimmen.

# 2. CHANGELOG ergänzen

# 3. Committen, taggen, schieben
git add -A
git commit -m "Release 1.1.0"
git tag v1.1.0
git push origin main --tags
```

Den Rest erledigt die Action. Läuft etwas schief, lässt sich ein Tag zurücknehmen:

```bash
git tag -d v1.1.0
git push origin :refs/tags/v1.1.0
```

## Versionsnummern

Nach [Semantic Versioning](https://semver.org/lang/de/):

- **Major** — bestehende Automationen müssen angepasst werden, etwa weil eine Eingabe umbenannt wurde.
- **Minor** — neue Funktion, bestehende Einrichtungen laufen unverändert weiter.
- **Patch** — Fehlerbehebung.

Wird eine Eingabe umbenannt oder entfernt, gehört ein Hinweis in den CHANGELOG. Nutzer müssen ihre Automation dann neu speichern.
