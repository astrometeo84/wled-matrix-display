# Änderungen

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.1](https://github.com/astrometeo84/wled-matrix-display/compare/v1.0.0...v1.0.1) (2026-09-23)


### Geändert

* code structure for improved readability and maintainability switch to uv ([9a226aa](https://github.com/astrometeo84/wled-matrix-display/commit/9a226aa3b64252e55161c7a852a77f35d1dfa741))

## [Unveröffentlicht]

### Geändert

- **Umstellung auf [uv](https://docs.astral.sh/uv/).** `requirements-dev.txt`
  und `pytest.ini` sind in die `pyproject.toml` gewandert, dazu kommt eine
  `uv.lock` mit festgezurrten Versionen. Lokal genügt jetzt `uv run pytest` –
  ohne virtuelle Umgebung von Hand anzulegen oder zu aktivieren, was
  besonders unter Windows die Execution-Policy-Hürde erspart.
- Die CI läuft mit `--locked`. Weichen `uv.lock` und `pyproject.toml`
  voneinander ab, bricht sie ab, statt stillschweigend andere Versionen zu
  installieren.
- Die uv-Version ist in beiden Workflows festgenagelt. `setup-uv` installiert
  ohne Angabe eine in der Action hinterlegte, oft ältere uv; die kennt das
  Format neuerer `uv.lock`-Dateien nicht und lässt `--locked` scheitern,
  obwohl lokal alles stimmt.
- Die `pyproject.toml` trägt keine Versionsnummer mehr, sondern einen
  eingefrorenen Platzhalter. Sonst hätte release-please sie angehoben, ohne
  die `uv.lock` nachzuziehen — und ausgerechnet die CI des Release-PR wäre
  daran gescheitert. Die Version steht jetzt allein im Blueprint-Kopf.
- `googleapis/release-please-action` auf v5 angehoben (Node-24-Laufzeit).

### Tests

- Drei Tests sichern die neue Regel ab: Platzhalter bleibt stehen,
  `pyproject.toml` taucht nicht wieder in `extra-files` auf, `uv.lock` und
  `pyproject.toml` nennen dieselbe Version.

## [1.0.0] – 2026-09-23

Erste Veröffentlichung. Der Blueprint wurde vor dem Release an einer echten
64×8-Matrix eingerichtet und getestet; die dabei gefundenen Stolperstellen sind
unten unter „Gelernt beim Testen" festgehalten.

### Enthalten

**Apps im Wechsel**

- Uhrzeit und Datum über die WLED-Platzhalter `#TIME` und `#DATE`
- Außentemperatur mit frei editierbarer Farbskala. Standard sind acht Stufen
  nach den Bezeichnungen des Deutschen Wetterdienstes: ab 25 °C Sommertag,
  ab 30 °C heißer Tag, ab 35 °C Wüstentag
- PV-Leistung mit drei Farbstufen und einstellbaren Schwellen
- Wärmepumpen-Verbrauch mit vier Farbstufen – Bereitschaft, normaler Betrieb,
  hohe Last und Heizstab – und einstellbaren Schwellen. Optional lässt sich das
  Vorzeichen umkehren, für Sensoren die den Verbrauch negativ zählen
- Anzahl offener Fenster aus beliebig vielen Kontakten
- Eigene Anzeigen als YAML-Liste, optional mit Anzeigebedingung
- Leistungssensoren in W oder kW werden automatisch erkannt
- Jede App blendet sich aus, wenn sie nichts zu melden hat
- Schriftgröße global und zusätzlich pro App einstellbar

**Nachrichten**

- Über das Event `wled_matrix_notify` aus beliebigen Automationen
- Optional über ein Texteingabefeld auf dem Dashboard
- Unterbrechen die Rotation, danach läuft sie weiter

**Anwesenheit und Stromsparen**

- Anzeige aus, wenn der Raum eine einstellbare Zeit leer ist
- Optional Stromtrennung über eine schaltbare Steckdose nach längerer Abwesenheit
- Bei Rückkehr Strom an, auf WLED warten, Anzeige an

**Bedienung**

- Elf Abschnitte, aufgeklappt sind nur Grundeinstellungen und Uhrzeit
- Pflicht ist allein die Auswahl der Matrix
- Die IP-Adresse wird aus der WLED-Integration gelesen

**Qualitätssicherung**

- 196 Tests, die die Vorlagen direkt aus der Blueprint-Datei lesen
- In der CI lädt Home Assistant den Blueprint mit zwei Testautomationen,
  einmal minimal und einmal mit allen Eingaben belegt

### Gelernt beim Testen

Diese Punkte haben sich erst am Gerät gezeigt und sind so gelöst:

- **Effekt-ID nicht raten.** Ein früherer Versuch leitete sie aus `effect_list`
  der WLED-Integration ab. Diese Liste ist aber anders sortiert als die
  Effekt-IDs der Firmware, das Ergebnis war ein falscher Effekt ohne
  Fehlermeldung. Die ID wird jetzt eingetragen, Standard 122; die verlässliche
  Quelle ist `http://IP/json/eff`. Der Wert 0 bedeutet: Effekt nicht umschalten.
- **Kein Gradzeichen.** Die eingebauten WLED-Schriften kennen `°` nicht, auf der
  Matrix blieb die Stelle leer. Die Einheit ist deshalb ein Textfeld mit `C`
  als Standard.
- **Leere Entitätsfelder.** Ein leerer Text ist kein gültiges `entity_id`.
  Blieben Anwesenheitssensor oder Texteingabefeld leer, ließ sich die Automation
  nicht speichern. Beide haben jetzt eine leere Liste als Standard.
- **Einheitliche Schrift.** Einige Apps hatten fest 5x8, die Uhr die eingestellte
  Schrift – die Schriftgröße sprang bei jedem Wechsel sichtbar.
- **Unsichtbare Apps erklären.** Bleibt die Wärmepumpe aus, liegt es fast immer
  am Vorzeichen oder an der Bereitschafts-Schwelle. Beides steht jetzt in den
  Feldbeschreibungen und in der Fehlersuche.
- **Leerzeichen vor der Einheit.** `PV 3.2 kW` statt `PV 3.2kW`; beim Gradzeichen
  bleibt es bewusst zusammen. Negative Werte entscheiden über den Betrag, welche
  Einheit gilt – `-2500 W` erschien vorher nicht als `-2.5 kW`.
