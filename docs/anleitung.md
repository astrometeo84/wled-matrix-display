# WLED-Matrix (64×8) als Info-Anzeige für Home Assistant

Ein einziger Blueprint macht aus deiner WLED-Matrix eine Anzeige wie die Ulanzi/Awtrix-Uhr: Apps im Wechsel, Benachrichtigungen dazwischen, und die Matrix schaltet sich ab, wenn niemand im Raum ist.

**Du brauchst genau zwei Dinge:** einen kleinen Eintrag in der `configuration.yaml` und **eine** Automation aus dem Blueprint. Keine Skripte, keine Szenen, keine Automation pro Nachricht.

| Datei | Zweck |
|---|---|
| `wled_matrix_display.yaml` | Der Blueprint – Apps, Nachrichten, Anwesenheit, Stromsparen |
| `README.md` | Diese Anleitung zum Abhaken |

---

## Was der Blueprint macht

**1. Apps (Dauer-Anzeigen im Wechsel)** — die Matrix wechselt alle 10 bis 60 Sekunden durch:

| App | Pflicht? | Anzeige |
|---|---|---|
| **Uhrzeit** | ✅ Grundanzeige | `#TIME` |
| Datum | optional | `#DATE` |
| Außentemperatur | Sensor auswählen | `7.3C` |
| PV-Leistung | Sensor auswählen | `PV 3.2kW`, Farbe nach Höhe |
| Wärmepumpen-Verbrauch | Sensor auswählen | `WP 820W` |
| Offene Fenster | Kontakte auswählen | `2 Fenster offen` |
| Eigene Apps | optional | frei als YAML-Liste |

Jede App schaltet sich selbst aus, wenn sie nichts zu sagen hat: kein PV-Ertrag nachts, Wärmepumpe steht, alle Fenster zu. Bei PV und Wärmepumpe erkennt der Blueprint automatisch, ob dein Sensor in W oder kW misst.

**2. Nachrichten** — unterbrechen die Rotation, danach läuft sie weiter. Zwei Wege:
- Über ein **Event**, das jede Automation auslösen kann.
- Über ein **Text-Eingabefeld** auf dem Dashboard.

**3. Anwesenheit & Stromsparen** — Anzeige aus bei leerem Raum, nach längerer Abwesenheit optional Strom trennen, bei Rückkehr automatisch wieder an.

---

## Checkliste

### Teil 1 – Voraussetzungen

- [ ] Die WLED-Matrix ist über die **offizielle WLED-Integration** in Home Assistant eingebunden.
- [ ] Die Matrix ist in WLED als **2D-Matrix mit 64×8 Pixeln** eingerichtet (WLED → Config → 2D Configuration).
- [ ] Die Matrix hat im Router eine **feste IP-Adresse**.
- [ ] Du hast einen Editor für die `configuration.yaml`, zum Beispiel „Studio Code Server“ oder „File editor“.

Diese Entitäten brauchst du später. Trag ein, was du hast, der Rest bleibt leer:

- [ ] Matrix: `light.____________________`
- [ ] Außentemperatur: `sensor.____________________`
- [ ] PV-Leistung: `sensor.____________________`
- [ ] Wärmepumpe: `sensor.____________________`
- [ ] Fenster-Kontakte: `binary_sensor.____________________`
- [ ] Anwesenheitssensor: `binary_sensor.____________________`
- [ ] Stromschalter der Matrix: `switch.____________________`

### Teil 2 – Effekt-ID herausfinden

Der Lauftext-Effekt hat in WLED eine Nummer. **122** passt bei den meisten Versionen, prüfen dauert aber nur eine Minute.

- [ ] Öffne im Browser `http://<IP-der-Matrix>/json/eff`.
- [ ] Suche `"Scrolling Text"` und zähle ab **0** ab, an welcher Stelle es steht.
- [ ] Notiere die Zahl, falls sie nicht 122 ist: `______`

> **Nicht über Home Assistant prüfen.** Die Effektliste der WLED-Integration ist **anders sortiert** als die Effekt-IDs der Firmware. Ein `effect_list.index('Scrolling Text')` im Template-Editor liefert deshalb eine falsche Zahl, und die Matrix zeigt dann irgendeinen anderen Effekt — ohne Fehlermeldung. Verlässlich ist nur `/json/eff` direkt von der Matrix.

**Alternative ohne Nummer:** Stell den Effekt „Scrolling Text“ einmal von Hand in der WLED-Oberfläche ein und trag im Blueprint bei der Effekt-ID eine **0** ein. Dann lässt der Blueprint den Effekt in Ruhe und ändert nur noch den Text. Praktisch, wenn die Nummer partout nicht passen will.

### Teil 3 – REST-Command anlegen

- [ ] Füge diesen Block in die `configuration.yaml` ein. Du musst nichts anpassen, die IP liefert der Blueprint.

```yaml
rest_command:
  wled_matrix_json:
    url: "http://{{ host }}/json/state"
    method: POST
    content_type: "application/json"
    payload: "{{ data if data is string else data | to_json }}"
```

> Gibt es schon einen Abschnitt `rest_command:`, fügst du nur den Teil ab `wled_matrix_json:` darunter ein. Der Abschnitt darf nicht doppelt vorkommen.

- [ ] Prüfe: Entwicklerwerkzeuge → YAML → **Konfiguration prüfen**.

### Teil 4 – Blueprint installieren

- [ ] Lege den Ordner `/config/blueprints/automation/wled_matrix/` an, falls er fehlt.
- [ ] Kopiere `wled_matrix_display.yaml` hinein.
- [ ] Starte Home Assistant neu.
- [ ] Prüfe unter Einstellungen → Automationen & Szenen → **Blueprints**, ob **„WLED Matrix – Alles-in-einem“** erscheint.
- [ ] Prüfe unter Entwicklerwerkzeuge → Aktionen, ob `rest_command.wled_matrix_json` vorhanden ist.

### Teil 5 – Automation erstellen

Klicke auf den Blueprint → **Automation erstellen**.

Du siehst elf Abschnitte, aber nur zwei sind aufgeklappt: **Grundeinstellungen** und **App – Uhrzeit**. Das sind die sechs Felder, die du wirklich brauchst. Alles andere ist optional und klappst du nur auf, wenn du es einrichten willst.

**Grundeinstellungen**
- [ ] **WLED-Matrix:** deine Matrix auswählen.
- [ ] **IP-Adresse:** leer lassen. Nur ausfüllen, wenn die Erkennung nicht klappt (siehe Fehlersuche).
- [ ] **Effekt-ID:** die Zahl aus Teil 2, meist 122. Oder **0**, wenn du den Effekt in WLED selbst eingestellt hast.

**App-Abschnitte** (jeder einzeln aufklappbar)
- [ ] **Uhrzeit anzeigen:** an lassen.
- [ ] **Datum:** nach Geschmack.
- [ ] **Außentemperatur:** Sensor auswählen oder leer lassen.
- [ ] **Außentemperatur:** Sensor auswählen. Die **Einheit** steht auf `C` und ergibt `7.3C`.
  - Ein Gradzeichen geht nicht: Die eingebauten WLED-Schriften kennen `°` nicht, auf der Matrix bleibt die Stelle leer. Alternativen sind `" C"` mit Leerzeichen, `" Grad"` oder ein leeres Feld.
  - Die **Farbskala** ist eine Liste von Stufen, jede mit `ab` (Temperatur) und `farbe`. Es gilt die höchste Stufe, deren `ab` nicht über dem Messwert liegt. Stufen kannst du ergänzen oder streichen; eine einzige Stufe ergibt eine feste Farbe.
- [ ] **PV-Leistung:** Sensor auswählen. Die beiden **Schwellen** legen fest, ab wann die mittlere und die hohe Farbe gelten — pass sie an deine Anlagengröße an.
- [ ] **Wärmepumpe:** Sensor auswählen. Vier Farbstufen mit drei Schwellen: Bereitschaft, normaler Betrieb, hohe Last und Heizstab.
  - Liefert dein Sensor den Verbrauch als **negative Zahl**, schalte **Vorzeichen umkehren** ein.
- [ ] **Fenster-Kontakte:** alle Kontakte auswählen, die mitgezählt werden sollen.
- [ ] *Optional:* **Eigene Apps** als Liste, zum Beispiel:

```yaml
- text: "{{ states('sensor.strompreis') | round(1) }}ct"
  color: [255, 255, 0]
  show: "{{ states('sensor.strompreis') | float(0) > 30 }}"
- text: "Akku {{ states('sensor.batterie') | int }}%"
  color: [120, 200, 255]
  font: "5x8"
```

**Darstellung**
- [ ] **App-Wechsel alle:** 15 Sekunden ist ein guter Start.
- [ ] **Schrift (Standard für alle Apps):** `6x8` ist gut lesbar, `5x8` zeigt mehr Zeichen. Die Zahl in Klammern ist der Wert, den WLED im Schieberegler für die Schriftgröße anzeigt.
  - Einzelne Apps können davon abweichen. Dafür gibt es bei jeder App ein Feld **Schrift**, das standardmäßig auf „wie eingestellt“ steht.
- [ ] **Geschwindigkeit, Helligkeit, vertikale Position** nach Geschmack.
- [ ] *Optional:* **Aktiv ab/bis**, zum Beispiel 06:00 bis 23:00 Uhr.

**Nachrichten**
- [ ] **Event-Name:** `wled_matrix_notify` stehen lassen.
- [ ] **Standardfarbe und -dauer** nach Geschmack.
- [ ] *Optional:* **Text-Eingabefeld**, siehe Teil 7.

**Anwesenheit & Stromsparen**
- [ ] **Anwesenheitssensor:** auswählen oder leer lassen. Leer heißt: Die Matrix läuft durchgehend.
  - Mehrere Sensoren? Unter Einstellungen → Geräte & Dienste → Helfer → **Gruppe → Binärsensor-Gruppe** zusammenfassen.
- [ ] **Anzeige aus nach:** zum Beispiel 5 Minuten.
- [ ] *Optional:* **Stromschalter** der Matrix. **Nicht die Matrix selbst auswählen!**
- [ ] **Strom trennen nach:** zum Beispiel 60 Minuten.
- [ ] Speichern.

### Teil 6 – Testen

- [ ] Schalte die Matrix in Home Assistant **ein**. Die Rotation läuft nur bei eingeschalteter Matrix.
- [ ] Warte eine Minute und beobachte, ob die Apps wechseln.
- [ ] Teste eine Nachricht: Entwicklerwerkzeuge → **Aktionen** → `event.fire`:

```yaml
action: event.fire
data:
  event_type: wled_matrix_notify
  event_data:
    text: "Test"
    color: [255, 0, 0]
    duration: 10
```

- [ ] Nach 10 Sekunden läuft die Rotation weiter.
- [ ] *Falls eingerichtet:* Verlasse den Raum. Nach X Minuten geht die Anzeige aus, später trennt der Strom. Beim Zurückkommen geht alles wieder an.

### Teil 7 – Nachrichten in eigenen Automationen

Für jede Benachrichtigung legst du eine **normale Automation** an (ohne Blueprint). Als Aktion feuerst du das Event:

```yaml
alias: "Matrix: Waschmaschine fertig"
triggers:
  - trigger: state
    entity_id: sensor.waschmaschine_status   # anpassen
    to: "fertig"
actions:
  - action: event.fire
    data:
      event_type: wled_matrix_notify
      event_data:
        text: "Waesche ist fertig!"
        color: [0, 255, 0]
        duration: 30
```

Mögliche Felder in `event_data`:

| Feld | Wirkung | Werte |
|---|---|---|
| `text` | **Pflicht.** Anzeigetext, max. 64 Zeichen | Text, `#TIME`, `#DATE` |
| `color` | Textfarbe | `[R, G, B]` |
| `duration` | Anzeigedauer | Sekunden |
| `gradient` / `color2` | Farbverlauf | `true`/`false`, `[R, G, B]` |
| `speed` | Scroll-Geschwindigkeit | 0–255 |
| `font` | Schriftgröße | `4x6`, `5x8`, `6x8` |
| `brightness` | Helligkeit | 1–255 |
| `y_offset` | vertikale Position | 0–255 |
| `reverse` | Laufrichtung umkehren | `true`/`false` |
| `trail` | Nachleuchten | 0–255 |

**Weiteres Beispiel – Tagesertrag bei Sonnenuntergang:**

```yaml
alias: "Matrix: PV-Tagesertrag"
triggers:
  - trigger: sun
    event: sunset
actions:
  - action: event.fire
    data:
      event_type: wled_matrix_notify
      event_data:
        text: "Heute {{ states('sensor.pv_ertrag_heute') | float(0) | round(1) }} kWh"
        gradient: true
        color: [255, 200, 0]
        color2: [255, 60, 0]
        duration: 60
```

### Teil 8 – Text vom Dashboard schicken (optional)

- [ ] Lege unter Einstellungen → Geräte & Dienste → **Helfer** → Text einen Helfer an, zum Beispiel „Matrix Nachricht“ (`input_text.matrix_nachricht`).
- [ ] Setze die **maximale Länge auf 64**.
- [ ] Trag den Helfer in der Automation unter **4 – Nachrichten → Text-Eingabefeld** ein.
- [ ] Leg den Helfer auf dein Dashboard.

Was du dort einträgst, erscheint sofort auf der Matrix. Das Feld wird danach automatisch geleert, damit der nächste Text wieder auslöst. So kannst du auch per Sprachassistent oder Handy-App Nachrichten schicken.

---

## Gut zu wissen

**Platz auf der Matrix:** Mit 64 Pixeln Breite passen etwa **10 Zeichen** in Schrift 6×8 und **12 Zeichen** in 5×8 auf einmal. Längeres läuft durch.

**Textlänge:** Maximal 64 Zeichen. Längeres wird automatisch abgeschnitten.

**Umlaute:** Die eingebauten Schriften können Umlaute teils nicht darstellen. Schreib `ae`, `oe`, `ue` und `ss`.

**Lauftext startet neu:** Jeder App-Wechsel und jede Nachricht startet den Text von vorn. Ist „App-Wechsel alle“ zu kurz für einen langen Text, wird er abgeschnitten. Dann das Intervall erhöhen oder den Text kürzen.

**Stromtrennung:**
- Die Steckdose muss für das Netzteil ausgelegt sein. Bei 512 LEDs und voller Helligkeit sind das mehrere Ampere bei 5 V.
- Nach dem Wiedereinschalten startet WLED mit seinem Boot-Preset. Das ist egal, weil die Rotation nach wenigen Sekunden übernimmt.
- Ein langer Wert bei „Strom trennen nach“ vermeidet ständiges Ein- und Ausschalten.

**Manuell ausschalten:** Schaltest du die Matrix in Home Assistant aus, bleibt sie aus. Die Rotation schaltet sie nicht wieder ein. Nur eine Nachricht schaltet sie kurz an.

---

## Fehlersuche

Was die Automation gemacht hat, siehst du unter Automation → drei Punkte → **Traces**.

| Problem | Lösung |
|---|---|
| Gar nichts passiert | Ist die Matrix eingeschaltet? Die Rotation läuft nur bei eingeschalteter Matrix. |
| Trace endet sofort an einer Bedingung | Prüfe der Reihe nach: Matrix an, Zeitfenster „Aktiv ab/bis“, Anwesenheitssensor, mindestens eine aktive App. |
| Immer nur die Uhr | Alle anderen Apps sind ausgeblendet: kein Sensor ausgewählt, oder die Bedingung greift (kein PV-Ertrag, WP aus, Fenster zu). |
| **Wärmepumpe erscheint nie** | Zwei häufige Gründe. **Erstens:** Sie läuft wirklich nicht — im Standby ziehen viele Anlagen nur 20 bis 50 W, das liegt unter der Schwelle von 100 W. Zum Prüfen „nur anzeigen, wenn sie läuft" kurz ausschalten. **Zweitens:** Das Vorzeichen passt nicht. Schau den Sensorwert unter Entwicklerwerkzeuge → Zustände an, während die Pumpe läuft: steht dort eine negative Zahl, muss „Vorzeichen umkehren" an sein, bei einer positiven aus. |
| **PV erscheint tagsüber nicht** | Sensorwert prüfen. Manche Wechselrichter liefern kleine negative Werte, dann greift „nur anzeigen, wenn Ertrag vorhanden". |
| IP wird nicht erkannt | IP im Abschnitt **Grundeinstellungen** von Hand eintragen. |
| Anderer Effekt statt Lauftext | Die Effekt-ID stimmt nicht. Richtigen Wert über `http://IP/json/eff` ermitteln (Teil 2). Nicht über die Effektliste in Home Assistant, die ist anders sortiert. |
| `rest_command` nicht gefunden | Nach dem Ändern der `configuration.yaml` wurde nicht neu gestartet. |
| Text zu groß oder abgeschnitten | Schrift `5x8` oder `4x6` wählen, vertikale Position anpassen. |
| PV zeigt falsche Größenordnung | Prüfe die Einheit des Sensors unter Entwicklerwerkzeuge → Zustände. Erkannt werden `W` und `kW`. |
| Anzeige geht bei Rückkehr nicht an | „Max. Wartezeit nach dem Einschalten“ erhöhen. Prüfen, ob WLED nach dem Einschalten ins WLAN kommt. |
| Nach einer langen Nachricht ein paar schnelle Wechsel | Normal: Während der Nachricht wartende App-Wechsel werden nachgeholt. |
| Blueprint erscheint nicht | Ordner und Dateiname aus Teil 4 prüfen und neu starten. |
