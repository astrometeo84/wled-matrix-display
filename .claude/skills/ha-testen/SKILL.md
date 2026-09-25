---
name: ha-testen
description: Den WLED-Matrix-Blueprint vor dem Commit im echten Home Assistant ausprobieren - Datei hinüberspielen, Konfiguration prüfen, Automationen neu laden, Zeichen direkt auf der Matrix testen.
---

# Blueprint im echten Home Assistant testen

Der Nutzer testet jede Änderung an seiner Matrix, bevor er committet. Die
Änderungen bleiben dabei im Arbeitsverzeichnis oder gestaged, es wird nichts
committet oder gepusht.

## 1. Vorher

```bash
uv run pytest && uv run yamllint --strict .
```

Schlägt etwas fehl, erst das beheben. Ein Blueprint, den die Tests ablehnen,
lädt Home Assistant oft gar nicht erst.

## 2. Hinüberspielen

```bash
uv run scripts/ha_deploy.py --trocken   # zeigt Ziel, ändert nichts
uv run scripts/ha_deploy.py
```

Das Skript kopiert die Datei aus dem Arbeitsverzeichnis, lässt Home Assistant
die Konfiguration prüfen und lädt die Automationen neu. Das liest auch die
Blueprints neu ein, ein Neustart ist nicht nötig.

Einstellungen stehen in `.ha.env` (Vorlage: `.ha.env.example`). Fehlt die
Datei, dem Nutzer die Vorlage zeigen und ihn bitten, sie anzulegen; den Token
nie selbst in eine Datei schreiben, die nicht in `.gitignore` steht, und nie
ausgeben.

Läuft Claude nicht auf dem Rechner des Nutzers (Cloud-Sitzung), kommt es an
Home Assistant nicht heran. Dann die Befehle nennen, der Nutzer führt sie aus.

## 3. Was der Nutzer prüfen soll

Passend zur Änderung eine kurze Liste geben, zum Beispiel:

- Automation öffnen: Sind neue Abschnitte und Felder da? Neue Eingaben
  ausfüllen und speichern, sonst gelten die Standardwerte.
- Ein paar Rotationen abwarten. Unter Automation → ⋮ → **Traces** in der
  Variable `apps` nachsehen, was der Blueprint berechnet hat.
- Grenzfälle am echten Sensor: Wert unter Entwicklerwerkzeuge → Zustände
  ansehen und mit der Anzeige vergleichen (Vorzeichen, Einheit, Schwellen).

## 4. Zeichen und Texte direkt auf der Matrix

Ob die Schrift ein Zeichen kennt, ohne den Blueprint testen, über
Entwicklerwerkzeuge → Aktionen (IP der Matrix einsetzen):

```yaml
action: rest_command.wled_matrix_json
data:
  host: 192.168.1.50
  data: >-
    {"on":true,"bri":128,"seg":[{"id":0,"fx":122,"n":"57% ↑↓ ^v +- °C","c2":128,"sx":128}]}
```

`c2` wählt die Schrift (0 / 64 / 128). Welche WLED-Version läuft, steht unter
`http://<IP>/json/info` im Feld `ver`. Bei 0.14/0.15 fehlen unbekannte Zeichen
einfach, bei 16 erscheint `?`.

## 5. Danach

Passt alles: Commit-Vorschlag im Conventional-Commits-Format nennen. Der
Nutzer committet selbst. Passt etwas nicht: weiter im Arbeitsverzeichnis
ändern und Schritt 2 wiederholen.
