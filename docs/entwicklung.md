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

## Im echten Home Assistant ausprobieren

Die Tests prüfen die Logik, nicht die Matrix. Vor dem Commit lohnt sich ein
Lauf an echter Hardware. `scripts/ha_deploy.py` spielt den Blueprint so, wie
er gerade im Arbeitsverzeichnis liegt, in Home Assistant, lässt die
Konfiguration prüfen und lädt die Automationen neu:

```bash
cp .ha.env.example .ha.env   # einmalig, dann ausfüllen
uv run scripts/ha_deploy.py --trocken
uv run scripts/ha_deploy.py
```

Kopiert wird über die Samba-Freigabe oder per `scp` über das SSH-Add-on. Für
Prüfung und Neuladen braucht das Skript einen langlebigen Zugriffstoken
(Profil → Sicherheit). `.ha.env` steht in `.gitignore`.

Für Claude liegen unter `.claude/skills/` zwei Anleitungen: `neue-app` listet
alle Stellen, die eine neue App berührt, `ha-testen` den Ablauf oben. Die
`CLAUDE.md` im Wurzelverzeichnis fasst die Regeln des Projekts zusammen.

## Wie die Tests aufgebaut sind

Die Tests lesen die Jinja-Vorlagen **direkt aus der Blueprint-Datei** statt Kopien davon zu prüfen. Änderst du den Blueprint, prüfen die Tests automatisch die neue Fassung. Dafür baut `tests/conftest.py` die Template-Umgebung von Home Assistant so weit nach, wie der Blueprint sie braucht: die Funktionen `states`, `state_attr`, `is_state`, `device_attr`, die Filter `bool` und `regex_replace`, und die Umwandlung des Ergebnisses in echte Python-Typen.

| Datei | Prüft |
|---|---|
| `tests/test_struktur.py` | Aufbau: Abschnitte, Eingaben, Selektoren, Trigger, Zweige |
| `tests/test_vorlagen.py` | Logik: IP-Erkennung, Einheiten, App-Liste, Rotation, Speicher |
| `tests/test_befehle.py` | Die JSON-Befehle, die tatsächlich an WLED gehen, samt Effekt-ID |
| `tests/test_deploy.py` | Das Hilfsskript `scripts/ha_deploy.py` |

Ein paar Tests sind bewusst streng, weil sie Fehler abfangen, die im Betrieb schwer zu finden sind:

- **Jede Eingabe wird benutzt.** Eine referenzierte, aber nicht definierte Eingabe lässt Home Assistant den Blueprint gar nicht erst laden.
- **Nur die Matrix ist Pflicht.** Alle anderen Felder brauchen einen Standardwert, sonst blockiert die Einrichtung.
- **Der Stromschalter darf keine Lampe sein.** Sonst könnte man versehentlich die Matrix selbst als ihren eigenen Stromschalter wählen.
- **Die Rotation schaltet die Matrix nie ein.** Eine von Hand ausgeschaltete Matrix soll ausgeschaltet bleiben.
- **Die Standardzeichen des Speichers sind ASCII.** Die eingebauten WLED-Schriften kennen nur ASCII 32 bis 126. Ein `↑` als Standard wäre bei WLED 0.14/0.15 unsichtbar und bei WLED 16 ein `?`.
- **Die Schriftwerte sind festgenagelt.** `0 / 64 / 128` sind durch WLED vorgegeben; verschieben sie sich, zeigt die Matrix eine andere Schrift als ausgewählt.

### Doppelte Wahrheiten vermeiden

Werte, die im Blueprint stehen, werden in den Tests **nicht noch einmal hingeschrieben**, sondern von dort gelesen. Sonst verdeckt eine richtige Kopie im Test einen Fehler im Blueprint. Die Schrifttabelle ist das Beispiel dafür: Sie kommt über `variables["fonts"]` aus der Datei. Nur an genau einer Stelle steht die erwartete Zuordnung ausgeschrieben, nämlich in `test_schriftwerte_entsprechen_wled`, und die dokumentiert eine Vorgabe von WLED.

### Taugen die Tests etwas?

Prüfen lässt sich das, indem man den Blueprint absichtlich kaputt macht und schaut, ob die Tests anschlagen. Diese sechsundzwanzig Änderungen werden erkannt:

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
| Lade- und Entladezeichen des Speichers vertauscht | ✅ |
| Vorzeichenumkehr des Speichers wirkungslos | ✅ |
| Ruhe-Schwelle des Speichers ignoriert oder ohne Betrag | ✅ |
| Speicher-Schwelle exklusiv statt inklusiv | ✅ |
| Speicher ohne Wert (`unavailable`) wird trotzdem angezeigt | ✅ |
| Unicode-Pfeil als Standardzeichen des Speichers | ✅ |
| Version wieder in der `pyproject.toml` gepflegt | ✅ |
| `pyproject.toml` wieder in `extra-files` eingetragen | ✅ |
| `uv.lock` und `pyproject.toml` mit verschiedenen Versionen | ✅ |

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

### `release-please.yml` — bei Push auf `main`

Hält einen Release-PR aktuell und veröffentlicht, sobald dieser gemergt wird.
Der Ablauf ist in **[CONTRIBUTING.md](../CONTRIBUTING.md)** beschrieben.

Zwei Dateien steuern das Verhalten:

| Datei | Inhalt |
|---|---|
| `.release-please-config.json` | Welche Datei die Version trägt, wie der CHANGELOG gegliedert wird |
| `.release-please-manifest.json` | Die aktuelle Version — pflegt der Bot selbst |

Die Version steht an **genau einer** Stelle: im Blueprint-Kopf, markiert mit
`# x-release-please-version`. Ein Test prüft, dass die Markierung noch da ist.
Ohne sie würde release-please die Datei stillschweigend unverändert lassen und
eine Version mit falscher Nummer ausliefern.

### Warum die pyproject.toml die Version nicht mitführt

Sie tat es anfangs, und das war ein Fehler. uv schreibt die Version des eigenen
Projekts in die `uv.lock`. Hebt release-please sie in der `pyproject.toml` an,
läuft die Sperrdatei weg — und die CI scheitert an `--locked`. Betroffen wäre
ausgerechnet der Release-PR selbst, also der eine PR, den man mergen will, um
zu veröffentlichen. Ein Henne-Ei-Problem, das man nur durch einen zusätzlichen
Commit im Branch des Bots auflösen könnte.

Deshalb steht dort jetzt `version = "0"`, eingefroren. Das Projekt wird nicht
als Paket gebaut (`package = false`), die Nummer ist reine Formalie. Drei Tests
halten das fest: einer, dass der Platzhalter stehen bleibt, einer, dass die
`pyproject.toml` nicht wieder in `extra-files` auftaucht, und einer, dass
`uv.lock` und `pyproject.toml` dieselbe Version nennen.

### Die uv-Version in den Workflows

`astral-sh/setup-uv` installiert ohne `version:`-Angabe nicht die neueste uv,
sondern die in der jeweiligen Action-Version hinterlegte. Ist die älter als die
lokal benutzte, kennt sie das Format der `uv.lock` nicht — die Datei trägt oben
ein Feld `revision`, das mit neueren uv-Versionen hochgezählt wird — und will
sie neu schreiben. `--locked` bricht dann ab, obwohl lokal `uv lock` nichts
mehr zu tun findet. Die Meldung lautet irreführend „To update the lockfile,
run `uv lock`".

Beide Workflows nageln die uv-Version daher fest. Beim Anheben der lokalen uv
diese Zeilen mitziehen.

Nach dem Veröffentlichen hängt ein zweiter Job die Blueprint-Datei ans Release
und lässt vorher `scripts/check_version.py` gegen den Tag laufen — ein
Sicherheitsnetz für den Fall, dass die Konfiguration kaputtgeht.

### Die Runner-Version

Alle Jobs laufen auf `ubuntu-26.04` statt auf `ubuntu-latest`. GitHub zieht
`ubuntu-latest` in Abständen auf die nächste Ubuntu-Version um, zuletzt ab
Oktober 2026 von 24.04 auf 26.04. Mit fester Version passiert so ein Wechsel
nicht unbemerkt zwischen zwei Läufen, sondern als eigener Commit, dessen CI
zeigt, ob alles weiterläuft.

Python kommt dabei nicht vom Runner, sondern über `setup-uv` in der jeweiligen
Version der Testmatrix, und Home Assistant läuft im Container. Ein Wechsel der
Ubuntu-Version ist deshalb meist unkritisch.

## Ein Release veröffentlichen

Von Hand ist dafür nichts zu tun. Version und CHANGELOG entstehen aus den
Commit-Nachrichten, siehe [CONTRIBUTING.md](../CONTRIBUTING.md). Du mergst nur
den Release-PR, wenn es soweit ist.

Soll ein Release zurückgenommen werden:

```bash
gh release delete v1.1.0 --yes
git push origin :refs/tags/v1.1.0
```

Danach die Version in `.release-please-manifest.json` auf den vorherigen Stand
setzen, sonst zählt der Bot von der gelöschten Version aus weiter.

## Versionsnummern

Nach [Semantic Versioning](https://semver.org/lang/de/), abgeleitet aus den
Commit-Präfixen:

- **Major** — `feat!:` oder `BREAKING CHANGE:`. Bestehende Automationen müssen angepasst werden, etwa weil eine Eingabe umbenannt wurde. Nutzer müssen ihre Automation dann öffnen und neu speichern.
- **Minor** — `feat:`. Neue Funktion, bestehende Einrichtungen laufen unverändert weiter.
- **Patch** — `fix:`. Fehlerbehebung.
